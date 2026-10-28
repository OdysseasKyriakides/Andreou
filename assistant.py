"""
LLM logic for Steps 3 and 4, shared by the Streamlit app and the batch runner.

Step 3  ask_log()          question -> LLM writes pandas code -> code runs on the real log
Step 4  summarize_trace()  case ID  -> facts computed by code -> LLM turns them into a narrative,
                           then every number in the narrative is checked against the facts
"""
import json
import re
from pathlib import Path

import pandas as pd

from llm import chat
from log_data import SCHEMA
from safe_exec import extract_code, run_code

# ---------------------------------------------------------------- Step 3
SYSTEM_STEP3 = f"""You are a process-mining data analyst. You answer questions about an insurance
claims event log by writing Python (pandas) code. You never invent numbers: every number in your
answer must be computed by the code from the data.

{SCHEMA}

Rules:
- Reply with ONE ```python code block and nothing else.
- `pd`, `np`, `px` (plotly.express), `events` and `cases` already exist. Do not import anything,
  do not read or write files.
- Assign:
    result = a pandas DataFrame with the answer (readable column names, rounded numbers)
    fig    = a plotly.express figure that visualises `result`, or None if a chart makes no sense
    answer = a short English sentence built with f-strings from the computed values
- "Waiting time" of an activity = waiting_min of that activity's events (time since the previous event).
  Ignore negative or missing waiting times and say so in `answer`.
- "Exceeded $X" refers to cost; decide from the question whether it means an event's cost or a
  claim's total_cost, and state your choice in `answer`.
"""

EXAMPLES_STEP3 = [
    "Show me all claims handled by User_A that exceeded $400",
    "Which activities have the longest waiting times and what is their percentage over the total?",
    "What is the total cost per user? Show it as a bar chart.",
    "How many claims follow each process variant?",
    "Show the average claim duration per week",
]


def ask_log(provider, model, api_key, question, events, cases):
    messages = [{"role": "user", "content": question}]
    seconds = tok_in = tok_out = 0
    error = None
    for attempt in range(2):  # one retry: the error is sent back so the LLM can fix its code
        reply = chat(provider, model, api_key, SYSTEM_STEP3, messages, step="3")
        seconds += reply["seconds"]
        tok_in += reply["input_tokens"]
        tok_out += reply["output_tokens"]
        code = extract_code(reply["text"])
        try:
            result, fig, answer = run_code(code, events, cases)
            error = None
            break
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
            result = fig = None
            answer = ""
            messages += [{"role": "assistant", "content": reply["text"]},
                         {"role": "user", "content": f"The code failed with {error}. Fix it."}]
    return {"answer": answer, "result": result, "fig": fig, "code": code, "error": error,
            "retries": attempt, "seconds": seconds, "input_tokens": tok_in, "output_tokens": tok_out}


# ---------------------------------------------------------------- Step 4
SYSTEM_STEP4 = """You are a process analyst at an insurance company. You receive the facts of ONE claim
(trace) as JSON, already computed from the event log, plus log-wide benchmarks.

Write a short narrative summary (4-6 sentences, plain English) for a manager:
- who registered the claim and how the case moved through the stages (users, waiting times),
- cost of the stages and the total cost compared with the average claim,
- the bottleneck: the stage with the longest wait compared with its usual (median) wait,
- any data-quality issues listed in the facts (e.g. a missing or suspicious timestamp), and that
  conclusions about that stage are therefore uncertain.

Strict rules: use ONLY numbers that appear in the JSON (you may round them). Do not compute new
numbers, do not invent causes, users or amounts. Write waiting times in hours if >= 60 minutes,
otherwise in minutes, using the given *_h or *_min fields."""


def _load_step1_issues(path="output/step1_errors.csv"):
    if not Path(path).exists():
        return {}
    from step1_report_docx import TYPES, classify
    err = pd.read_csv(path, dtype=str, keep_default_na=False)
    ev = err.groupby("row").agg(case=("case", "first"), activity=("activity", "first"),
                                ts_raw=("ts_raw", "first"), checks=("check", lambda s: ", ".join(sorted(set(s)))))
    issues = {}
    for _, r in ev.iterrows():
        t = classify(r["checks"], r["ts_raw"])
        issues.setdefault(r["case"], []).append(
            {"activity": r["activity"], "type": TYPES[t][0], "raw_timestamp": r["ts_raw"] or "(empty)"})
    return issues


STEP1_ISSUES = _load_step1_issues()


def trace_facts(case, events, cases):
    ev = events[events["case"] == case].sort_values("position")
    if ev.empty:
        raise ValueError(f"{case} not found")
    pos_wait = events[events["waiting_min"] > 0]
    median_wait = pos_wait.groupby("activity")["waiting_min"].median()
    c = cases[cases["case"] == case].iloc[0]

    stages = []
    for _, e in ev.iterrows():
        w = e["waiting_min"]
        med = median_wait.get(e["activity"])
        stages.append({
            "stage": int(e["position"]), "activity": e["activity"], "user": e["user"],
            "timestamp": "missing" if pd.isna(e["timestamp"]) else e["timestamp"].strftime("%Y-%m-%d %H:%M"),
            "cost_usd": int(e["cost"]),
            "wait_since_previous_min": None if pd.isna(w) else round(w),
            "wait_since_previous_h": None if pd.isna(w) else round(w / 60, 1),
            "usual_wait_median_min": None if med is None or e["position"] == 1 else round(med),
        })
    valid = [s for s in stages if s["wait_since_previous_min"] and s["wait_since_previous_min"] > 0
             and s["usual_wait_median_min"]]
    bottleneck = "none: no stage waited at least 1.2x its usual (median) wait"
    b = max(valid, key=lambda s: s["wait_since_previous_min"] / s["usual_wait_median_min"]) if valid else None
    if b and b["wait_since_previous_min"] / b["usual_wait_median_min"] >= 1.2:
        bottleneck = {"stage": b["stage"], "activity": b["activity"], "wait_min": b["wait_since_previous_min"],
                      "wait_h": b["wait_since_previous_h"], "usual_wait_min": b["usual_wait_median_min"],
                      "times_usual": round(b["wait_since_previous_min"] / b["usual_wait_median_min"], 1)}
    return {
        "case": case,
        "variant": c["variant"],
        "is_standard_variant": c["variant"] == cases["variant"].mode()[0],
        "stages": stages,
        "total_cost_usd": int(c["total_cost"]),
        "average_claim_cost_usd": round(cases["total_cost"].mean()),
        "duration_h": None if pd.isna(c["duration_h"]) else round(c["duration_h"], 1),
        "median_claim_duration_h": round(cases["duration_h"].median(), 1),
        "bottleneck": bottleneck,
        "data_quality_issues": STEP1_ISSUES.get(case, []),
    }


def _numbers_in(obj):
    if isinstance(obj, bool) or obj is None:
        return []
    if isinstance(obj, (int, float)):
        return [float(obj)]
    if isinstance(obj, dict):
        return [n for v in obj.values() for n in _numbers_in(v)]
    if isinstance(obj, list):
        return [n for v in obj for n in _numbers_in(v)]
    return []


def check_numbers(text, facts):
    """Every number the LLM wrote must match a number in the facts (rounding allowed).
    Dates, times, case/user IDs and small counts (<= 10, e.g. 'stage 3') are skipped."""
    known = [abs(k) for k in _numbers_in(facts)]  # "-15 min" is written as "15 minutes earlier" too
    clean = re.sub("[‐-―−]", "-", text)  # LLMs often write non-ASCII dashes in dates
    clean = re.sub(r"\d{4}-\d{2}-\d{2}(?:T\d{2}(?::\d{2})*)?|\d{1,2}:\d{2}|Case_\d+|User_\w+|20\d\d", " ", clean)
    found = [float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*(?:\.\d+)?", clean)]
    found = [x for x in found if x > 10]
    unverified = [x for x in found if not any(abs(x - k) <= max(0.6, 0.02 * k) for k in known)]
    return {"numbers": len(found), "verified": len(found) - len(unverified), "unverified": unverified}


def summarize_trace(provider, model, api_key, case, events, cases):
    facts = trace_facts(case, events, cases)
    reply = chat(provider, model, api_key, SYSTEM_STEP4,
                 [{"role": "user", "content": json.dumps(facts, indent=1)}], step="4")
    return {"text": reply["text"].strip(), "facts": facts, "check": check_numbers(reply["text"], facts),
            "seconds": reply["seconds"], "input_tokens": reply["input_tokens"],
            "output_tokens": reply["output_tokens"]}
