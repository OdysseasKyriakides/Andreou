"""
Step 5 - Fix the timestamp errors with two LLMs x two methods (statistical, machine learning).

Same pattern as Step 3: the LLM never edits timestamps itself. It writes Python code that
DETECTS and CORRECTS the wrong timestamps; the app runs that code on the real log.
The generated code is a reusable function of `events`, so we can also run it on logs with
synthetic errors whose true values are known (that is how correction accuracy is measured).

    generate_fix()   LLM writes the code (with up to 3 retries if it fails), runs it on the real log
    evaluate_fix()   scores the code: detection vs the Step 1 ground truth (real log) and
                     detection + MAE + order restored on synthetic errors (known truth)

Shared by the Streamlit app (tab "Step 5") and the batch runner step5_run_both.py.
"""
import time

import numpy as np
import pandas as pd

from assistant import check_numbers
from llm import chat
from log_data import CSV, build_cases, load_events
from safe_exec import describe_error, extract_code, run_fix_code

ORDER = ["Register Claim", "Verify Documents", "Evaluate Claim", "Approve Claim", "Close Claim"]
STANDARD_VARIANT = " -> ".join(ORDER)
METHODS = ["Statistical", "ML"]

# ---------------------------------------------------------------- prompts
SYSTEM_STEP5 = """You are a process-mining data engineer. An insurance-claims event log contains wrong
timestamps. You write Python (pandas) code that DETECTS the wrong timestamps and CORRECTS them.

DataFrame `events` (one row per event, 500 rows, 100 claims, ordered by case and position):
  case (str, e.g. 'Case_7'), case_num (int), position (int, 1..5 = order of the event in its case),
  activity (str), timestamp (datetime64, NaT if missing or unparseable),
  timestamp_raw (str as written in the file, NaN if empty), user (str 'User_A'..'User_E'),
  cost (int, $), waiting_min (float, minutes since the previous event of the case, NaN/negative possible)

What is known about the log:
- Every claim follows Register Claim -> Verify Documents -> Evaluate Claim -> Approve Claim -> Close Claim
  (confirmed by process discovery on the error-free claims). `position` follows this order.
- All events of a claim happen on the same day, a few hours apart.
- Kinds of timestamp errors in the log (you do NOT know which events are affected; your code must find them):
    missing      timestamp is NaT (timestamp_raw is empty)
    incomplete   timestamp_raw has only date and hour, e.g. '2026-09-13T16' (the minutes are lost)
    out of order an event's timestamp is not after the timestamp of the activity before it

Rules:
- Reply with ONE ```python code block and nothing else.
- `pd`, `np` and `events` already exist. You may import only pandas, numpy, sklearn, datetime, math.
  Do not read or write files.
- Pandas tips (common mistakes): durations are pd.Timedelta(minutes=x) (capital D only in "Timedelta");
  the midpoint of two timestamps a < b is a + (b - a) / 2 (never a + b); pass only numeric/bool columns to
  model.fit / model.predict (never datetime columns); keep timestamp_fixed as datetime64 and fill it with
  pd.Timestamp values; clip predicted waiting times to the range seen in the valid data.
- At the end assign:
    fixed  = a copy of `events` with the same 500 rows and two new columns:
               is_error        (bool) True where the original timestamp is wrong and you replaced it
               timestamp_fixed (datetime64) the corrected timestamp; equal to `timestamp` where
                               is_error is False; never NaT
    answer = a short English summary built with f-strings from computed values: how many events and
             claims were corrected, per kind of error, and which statistics / model you used.
"""

METHOD_PROMPTS = {
    "Statistical": """METHOD: STATISTICAL (descriptive statistics only, no machine learning).
Compute, from the events with valid timestamps, the typical waiting time between each pair of consecutive
activities of the normative order (use the median: it is robust to the outliers caused by the errors).
Then rebuild every wrong timestamp from the neighbouring valid timestamps of the same claim with these
statistics. Write the code now.""",
    "ML": """METHOD: MACHINE LEARNING (regression).
The classes RandomForestRegressor, GradientBoostingRegressor, LinearRegression and KNeighborsRegressor
(scikit-learn) already exist, no import needed. Train ONE of them (random_state=42 where possible) on the
events with valid timestamps, to predict waiting_min (minutes since the previous activity) from features
known for every event, e.g. activity, user, cost, hour and weekday of the claim (encode categories with
pd.get_dummies). Then rebuild every wrong timestamp from the previous valid timestamp of the claim plus the
predicted waiting time. Name the model and its features in `answer`. Write the code now.""",
}


# ---------------------------------------------------------------- generate + run
def generate_fix(provider, model, method, events, max_retries=3):
    messages = [{"role": "user", "content": METHOD_PROMPTS[method]}]
    seconds = tok_in = tok_out = 0
    error = fixed = None
    answer = code = ""
    errors = []
    for attempt in range(max_retries + 1):
        reply = chat(provider, model, SYSTEM_STEP5, messages, step=f"5-{method}")
        seconds += reply["seconds"]
        tok_in += reply["input_tokens"]
        tok_out += reply["output_tokens"]
        code = extract_code(reply["text"])
        try:
            fixed, answer = run_fix_code(code, events)
            error = None
            break
        except Exception as e:
            error = describe_error(e, code)
            errors.append(error)
            messages += [{"role": "assistant", "content": reply["text"]},
                         {"role": "user", "content": f"The code failed with {error}. Fix it and reply with the "
                                                     f"full corrected code block."}]
    return {"provider": provider, "model": model, "method": method, "code": code, "fixed": fixed,
            "answer": answer, "error": error, "errors": errors, "retries": attempt,
            "seconds": seconds, "input_tokens": tok_in, "output_tokens": tok_out}


# ---------------------------------------------------------------- ground truth (Step 1) and synthetic errors
def step1_error_cases(path="output/step1_errors.csv"):
    return set(pd.read_csv(path, dtype=str)["case"])


def inject_errors(seed, per_type=5, csv=CSV):
    """Copy of the raw log with synthetic errors in error-free claims (the true values are kept).
    Types mimic Step 1: A missing, B hour only, C Approve 15 min before Evaluate, D Evaluate/Approve swapped."""
    raw = pd.read_csv(csv, dtype=str, keep_default_na=False)
    rng = np.random.default_rng(seed)
    clean = sorted(set(raw["CaseID"]) - step1_error_cases(), key=lambda c: int(c.split("_")[1]))
    picked = rng.choice(clean, size=4 * per_type, replace=False)
    truth = []  # one row per altered event: case, activity, type, true timestamp

    def idx(case, act):
        return raw.index[(raw["CaseID"] == case) & (raw["Activity"] == act)][0]

    for k, case in enumerate(picked):
        kind = "ABCD"[k // per_type]
        if kind in "AB":
            act = ORDER[rng.integers(len(ORDER))]
            i = idx(case, act)
            truth.append((case, act, kind, raw.at[i, "Timestamp"]))
            raw.at[i, "Timestamp"] = "" if kind == "A" else raw.at[i, "Timestamp"][:13]
        elif kind == "C":
            ie, ia = idx(case, "Evaluate Claim"), idx(case, "Approve Claim")
            truth.append((case, "Approve Claim", kind, raw.at[ia, "Timestamp"]))
            shifted = pd.Timestamp(raw.at[ie, "Timestamp"]) - pd.Timedelta(minutes=15)
            raw.at[ia, "Timestamp"] = shifted.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            ie, ia = idx(case, "Evaluate Claim"), idx(case, "Approve Claim")
            truth += [(case, "Evaluate Claim", kind, raw.at[ie, "Timestamp"]),
                      (case, "Approve Claim", kind, raw.at[ia, "Timestamp"])]
            raw.at[ie, "Timestamp"], raw.at[ia, "Timestamp"] = raw.at[ia, "Timestamp"], raw.at[ie, "Timestamp"]
    truth = pd.DataFrame(truth, columns=["case", "activity", "type", "true_ts"])
    truth["true_ts"] = pd.to_datetime(truth["true_ts"])
    return raw, truth, set(clean)


# ---------------------------------------------------------------- metrics
def prf(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true, bool), np.asarray(y_pred, bool)
    tp, fp = int((y_true & y_pred).sum()), int((~y_true & y_pred).sum())
    fn, tn = int((y_true & ~y_pred).sum()), int((~y_true & ~y_pred).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "accuracy": (tp + tn) / len(y_true),
            "precision": precision, "recall": recall, "f1": f1}


def _clean_fixed(fixed, events):
    """Align the LLM output with `events` (same case/position) and normalise the column types."""
    f = fixed.copy()
    if "position" not in f.columns:
        f["position"] = f.groupby("case").cumcount() + 1
    f = events[["case", "position", "activity", "timestamp"]].merge(
        f[["case", "position", "is_error", "timestamp_fixed"]], on=["case", "position"], how="left")
    f["is_error"] = f["is_error"].fillna(False).astype(bool)
    f["timestamp_fixed"] = pd.to_datetime(f["timestamp_fixed"], errors="coerce")
    return f


def _in_order(f):
    """Per case: True if the corrected timestamps put the 5 activities in the normative order."""
    v = (f.dropna(subset=["timestamp_fixed"]).sort_values(["case", "timestamp_fixed"], kind="stable")
         .groupby("case")["activity"].apply(" -> ".join))
    return v == STANDARD_VARIANT


def contract_checks(fixed, events):
    """Ways the generated code can break its own contract (counted as hallucination / invalid output)."""
    f = _clean_fixed(fixed, events)
    silent = (~f["is_error"] & f["timestamp"].notna() & (f["timestamp_fixed"] != f["timestamp"])).sum()
    return {"rows_ok": len(fixed) == len(events), "nat_left": int(f["timestamp_fixed"].isna().sum()),
            "silent_changes": int(silent)}


def answer_check(answer, f):
    """Numbers > 10 in the LLM's own summary must match counts of its corrected log."""
    facts = {"events_flagged": int(f["is_error"].sum()), "cases_flagged": int(f.loc[f["is_error"], "case"].nunique()),
             "events": len(f), "cases": int(f["case"].nunique()),
             "per_activity": f[f["is_error"]].groupby("activity").size().tolist()}
    return check_numbers(answer, facts)


def evaluate_fix(code, events, fixed, answer, seeds=(1, 2, 3, 4, 5)):
    """Scores one generated correction. Returns a flat dict of metrics + per-type MAE."""
    f = _clean_fixed(fixed, events)
    gt = step1_error_cases()
    by_case = f.groupby("case")["is_error"].any()
    det = prf(by_case.index.isin(gt), by_case.values)
    order = _in_order(f)
    out = {f"real_{k}": v for k, v in det.items()}
    out["real_cases_in_order"] = float(order.reindex(by_case.index, fill_value=False).mean())
    out["real_error_cases_in_order"] = float(order.reindex(sorted(gt), fill_value=False).mean())
    out.update(contract_checks(fixed, events))
    chk = answer_check(answer, f)
    out["answer_numbers"], out["answer_unverified"] = chk["numbers"], len(chk["unverified"])

    # synthetic errors: the same code runs on logs whose true timestamps are known
    syn, abs_err, runtimes = [], [], []
    for seed in seeds:
        raw, truth, clean = inject_errors(seed)
        ev = load_events(raw)
        t0 = time.perf_counter()
        try:
            sfixed, _ = run_fix_code(code, ev)
            runtimes.append(time.perf_counter() - t0)
        except Exception as e:  # the code worked on the real log but fails on a new one = not robust
            syn.append({"seed": seed, "failed": f"{type(e).__name__}: {e}"})
            continue
        sf = _clean_fixed(sfixed, ev)
        sf = sf[sf["case"].isin(clean)]  # only claims whose truth is known
        sf = sf.merge(truth, on=["case", "activity"], how="left")
        d = prf(sf["true_ts"].notna(), sf["is_error"])
        hit = sf[sf["true_ts"].notna()].copy()
        hit["abs_err_min"] = (hit["timestamp_fixed"] - hit["true_ts"]).abs().dt.total_seconds() / 60
        abs_err.append(hit[["type", "abs_err_min"]])
        within = float((hit["abs_err_min"] <= 60).mean())
        o = _in_order(sf).reindex(truth["case"].unique(), fill_value=False)
        syn.append({"seed": seed, **d, "mae_min": hit["abs_err_min"].mean(),
                    "median_ae_min": hit["abs_err_min"].median(), "within_60min": within,
                    "unrepaired": int(hit["abs_err_min"].isna().sum()), "order_restored": float(o.mean())})
    syn = pd.DataFrame(syn)
    ok = syn[syn["failed"].isna()] if "failed" in syn.columns else syn
    out["syn_runs_failed"] = int(len(syn) - len(ok))
    for k in ["accuracy", "precision", "recall", "f1", "mae_min", "median_ae_min", "within_60min",
              "order_restored", "unrepaired"]:
        out[f"syn_{k}"] = float(ok[k].mean()) if len(ok) else np.nan
    if abs_err:
        e = pd.concat(abs_err)
        for t, g in e.groupby("type"):
            out[f"syn_mae_{t}"] = float(g["abs_err_min"].mean())
    out["fix_runtime_s"] = float(np.mean(runtimes)) if runtimes else np.nan
    return out, syn


def corrected_log(fixed, events):
    """Corrected log in the original file format (+ is_error), for download and re-mining."""
    f = _clean_fixed(fixed, events).merge(events[["case", "position", "user", "cost", "timestamp_raw"]],
                                          on=["case", "position"])
    return pd.DataFrame({"CaseID": f["case"], "Activity": f["activity"],
                         "Timestamp": f["timestamp_fixed"].dt.strftime("%Y-%m-%dT%H:%M:%S"),
                         "User": f["user"], "Cost": f["cost"], "OriginalTimestamp": f["timestamp_raw"],
                         "IsError": f["is_error"]})


def changes_table(fixed, events):
    f = _clean_fixed(fixed, events).merge(events[["case", "position", "timestamp_raw"]], on=["case", "position"])
    c = f[f["is_error"]].copy()
    c["fixed"] = c["timestamp_fixed"].dt.strftime("%Y-%m-%d %H:%M")
    c["in_step1"] = c["case"].isin(step1_error_cases())
    return c[["case", "activity", "timestamp_raw", "fixed", "in_step1"]].rename(
        columns={"timestamp_raw": "original", "in_step1": "case in Step 1 list"})
