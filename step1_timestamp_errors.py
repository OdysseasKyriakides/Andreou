"""
Step 1 - Detect timestamp errors in the insurance-claims event log.

Every finding is produced by code (pandas + PM4PY), not by an LLM.

Usage:
    python step1_timestamp_errors.py --csv data/log.csv [--xes data/log.xes]
    (column names are auto-detected; override with --case/--activity/--timestamp)

Outputs (in ./output):
    step1_errors.csv      one row per suspicious event, with the check that flagged it
    step1_summary.txt     counts per check + log statistics
"""
import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pm4py


# ---------------------------------------------------------------- loading
def guess_column(columns, keywords):
    for kw in keywords:
        for c in columns:
            if kw in c.lower():
                return c
    return None


def load_csv(path, case_col, act_col, ts_col):
    # Read everything as text first so we can inspect the raw timestamp format
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    cols = list(df.columns)
    case_col = case_col or guess_column(cols, ["case:concept:name", "case", "claim"])
    act_col = act_col or guess_column(cols, ["concept:name", "activity", "event", "task"])
    ts_col = ts_col or guess_column(cols, ["time:timestamp", "timestamp", "time", "date"])
    if not all([case_col, act_col, ts_col]):
        raise SystemExit(f"Could not detect columns in {cols}. Use --case/--activity/--timestamp.")
    print(f"Columns -> case: {case_col!r}, activity: {act_col!r}, timestamp: {ts_col!r}")

    df = df.rename(columns={case_col: "case", act_col: "activity", ts_col: "ts_raw"})
    df["row"] = np.arange(len(df)) + 2  # line number in the CSV file (header = line 1)
    df["file_pos"] = df.groupby("case").cumcount()  # position of the event inside its case, as written in the file
    df["ts"] = pd.to_datetime(df["ts_raw"].str.strip(), format="mixed", errors="coerce", utc=True)
    return df


# ---------------------------------------------------------------- checks
findings = []


def flag(rows, check, detail):
    for _, r in rows.iterrows():
        d = detail(r) if callable(detail) else detail
        findings.append({"row": r["row"], "case": r["case"], "activity": r["activity"],
                         "ts_raw": r["ts_raw"], "check": check, "detail": d})


def check_missing_or_unparseable(df):
    bad = df[df["ts"].isna()]
    flag(bad, "1_missing_or_unparseable", "timestamp is empty or not a valid date")


def check_format_consistency(df):
    # Replace digits with 9 and letters with A, so '2024-03-05 10:00:00' -> '9999-99-99 99:99:99'
    pattern = df["ts_raw"].str.replace(r"\d", "9", regex=True).str.replace(r"[A-Za-z]", "A", regex=True)
    counts = pattern.value_counts()
    main = counts.index[0]
    print(f"\nTimestamp formats found:\n{counts.to_string()}")
    odd = df[pattern != main]
    flag(odd, "2_format_inconsistent", lambda r: f"format differs from dominant '{main}'")


def check_out_of_range(df):
    ts = df["ts"].dropna()
    q1, q3 = ts.quantile(0.25), ts.quantile(0.75)
    iqr = q3 - q1
    low, high = q1 - 3 * iqr, q3 + 3 * iqr
    mask = df["ts"].notna() & ((df["ts"] < low) | (df["ts"] > high))
    flag(df[mask], "3_out_of_range",
         lambda r: f"outside log period [{low.date()} .. {high.date()}]")


def check_file_order(df):
    # Events of a case written later in the file but with an earlier timestamp
    d = df.dropna(subset=["ts"]).sort_values(["case", "file_pos"])
    prev = d.groupby("case")["ts"].shift()
    prev_act = d.groupby("case")["activity"].shift()
    bad = d[d["ts"] < prev].copy()
    bad["prev_act"] = prev_act[bad.index]
    bad["prev_ts"] = prev[bad.index]
    flag(bad, "4_earlier_than_previous_event",
         lambda r: f"{(r['prev_ts'] - r['ts']).total_seconds() / 60:.0f} min earlier than "
                   f"previous event '{r['prev_act']}' ({r['prev_ts']:%Y-%m-%d %H:%M})")


def check_precedence(df, min_support=0.8, min_cases=10):
    """Learn 'A always happens before B' rules from the data itself,
    then flag cases that violate a rule (e.g. Close Claim before Register Claim)."""
    first = (df.dropna(subset=["ts"]).groupby(["case", "activity"])
               .agg(ts=("ts", "min"), row=("row", "min"), ts_raw=("ts_raw", "first")).reset_index())
    acts = first["activity"].unique()
    wide = first.pivot(index="case", columns="activity", values="ts")
    rules = []
    for a in acts:
        for b in acts:
            if a == b:
                continue
            both = wide[[a, b]].dropna()
            if len(both) < min_cases:
                continue
            before = (both[a] < both[b]).mean()
            if before >= min_support:
                rules.append((a, b, before, len(both)))
                viol = both[both[a] > both[b]].index
                rows = first[(first["case"].isin(viol)) & (first["activity"] == b)]
                flag(rows, "5_precedence_violation",
                     lambda r, a=a, before=before: f"'{r['activity']}' happens before '{a}', "
                                                   f"but '{a}' comes first in {before:.0%} of cases")
    print(f"\nPrecedence rules learned from data (support >= {min_support:.0%}): {len(rules)}")
    return rules


def check_duplicates(df):
    d = df.dropna(subset=["ts"])
    dup = d[d.duplicated(subset=["case", "ts"], keep=False)]
    flag(dup, "6_same_timestamp_in_case", "another event of the same case has the identical timestamp")


def check_duration_outliers(df, k=3.0):
    """Waiting time between consecutive events (sorted by time); per transition,
    flag durations that are extreme on a log scale (IQR rule)."""
    d = df.dropna(subset=["ts"]).sort_values(["case", "ts"]).copy()
    d["prev_act"] = d.groupby("case")["activity"].shift()
    d["wait_h"] = d.groupby("case")["ts"].diff().dt.total_seconds() / 3600
    d = d.dropna(subset=["prev_act"])
    d["log_wait"] = np.log1p(d["wait_h"].clip(lower=0))
    for (a, b), g in d.groupby(["prev_act", "activity"]):
        if len(g) < 8:
            continue
        q1, q3 = g["log_wait"].quantile([0.25, 0.75])
        iqr = q3 - q1
        if iqr == 0:
            continue
        out = g[(g["log_wait"] > q3 + k * iqr) | (g["log_wait"] < q1 - k * iqr)]
        med = g["wait_h"].median()
        flag(out, "7_duration_outlier",
             lambda r, a=a, med=med: f"wait after '{a}' = {r['wait_h']:.1f} h (median {med:.1f} h)")


def suggest_day_month_swap(df, err):
    """For flagged events with day<=12, test if swapping day and month gives a
    timestamp that fits between the neighbouring events of the case."""
    sugg = {}
    d = df.sort_values(["case", "file_pos"])
    for row in err["row"].unique():
        r = d[d["row"] == row].iloc[0]
        t = r["ts"]
        if pd.isna(t) or t.day > 12 or t.day == t.month:
            continue
        try:
            swapped = t.replace(month=t.day, day=t.month)
        except ValueError:
            continue
        case = d[d["case"] == r["case"]]
        prev = case[case["file_pos"] < r["file_pos"]]["ts"].max()
        nxt = case[case["file_pos"] > r["file_pos"]]["ts"].min()
        if (pd.isna(prev) or swapped >= prev) and (pd.isna(nxt) or swapped <= nxt):
            sugg[row] = str(swapped)
    return sugg


def check_xes_vs_csv(df, xes_path):
    xes = pm4py.read_xes(str(xes_path))
    xes = xes.rename(columns={"case:concept:name": "case", "concept:name": "activity",
                              "time:timestamp": "ts_xes"})
    xes["case"] = xes["case"].astype(str)
    xes["file_pos"] = xes.groupby("case").cumcount()
    m = df.merge(xes[["case", "activity", "file_pos", "ts_xes"]],
                 on=["case", "activity", "file_pos"], how="left")
    m["ts_xes"] = pd.to_datetime(m["ts_xes"], utc=True)
    diff = m[m["ts"].notna() & m["ts_xes"].notna() & (m["ts"] != m["ts_xes"])]
    flag(diff, "8_csv_xes_mismatch", lambda r: f"XES has {r['ts_xes']}")
    print(f"\nCSV vs XES: {len(diff)} events with different timestamps")


# ---------------------------------------------------------------- PM4PY overview
def pm4py_overview(df):
    log = df.dropna(subset=["ts"]).copy()
    log = pm4py.format_dataframe(log, case_id="case", activity_key="activity", timestamp_key="ts")
    durations_h = np.array(pm4py.get_all_case_durations(log)) / 3600
    variants = pm4py.get_variants(log)
    start = pm4py.get_start_activities(log)
    end = pm4py.get_end_activities(log)
    lines = [
        f"Cases: {log['case:concept:name'].nunique()}  Events: {len(log)}",
        f"Activities: {sorted(log['concept:name'].unique())}",
        f"Start activities: {start}",
        f"End activities: {end}",
        f"Variants: {len(variants)}",
        f"Case duration (h): min {durations_h.min():.1f}, median {np.median(durations_h):.1f}, "
        f"max {durations_h.max():.1f}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--xes")
    ap.add_argument("--case")
    ap.add_argument("--activity")
    ap.add_argument("--timestamp")
    ap.add_argument("--out", default="output")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(exist_ok=True)
    df = load_csv(args.csv, args.case, args.activity, args.timestamp)

    check_missing_or_unparseable(df)
    check_format_consistency(df)
    check_out_of_range(df)
    check_file_order(df)
    check_precedence(df)
    check_duplicates(df)
    check_duration_outliers(df)
    if args.xes:
        check_xes_vs_csv(df, args.xes)

    err = pd.DataFrame(findings, columns=["row", "case", "activity", "ts_raw", "check", "detail"])
    order_checks = ["3_out_of_range", "4_earlier_than_previous_event", "5_precedence_violation"]
    swaps = suggest_day_month_swap(df, err[err["check"].isin(order_checks)])
    err["day_month_swap_fits"] = err["row"].map(swaps)
    err = err.sort_values(["case", "row", "check"])
    err.to_csv(out / "step1_errors.csv", index=False)

    summary = [
        "=== Log overview (PM4PY) ===", pm4py_overview(df), "",
        "=== Findings per check ===", err["check"].value_counts().sort_index().to_string(), "",
        f"Distinct suspicious events: {err['row'].nunique()}",
        f"Cases affected: {err['case'].nunique()} / {df['case'].nunique()}",
        f"Events where a day/month swap would fix the order: {len(swaps)}",
    ]
    text = "\n".join(summary)
    (out / "step1_summary.txt").write_text(text, encoding="utf-8")
    print("\n" + text)
    print(f"\nDetails -> {out / 'step1_errors.csv'}")


if __name__ == "__main__":
    main()
