"""
Shared helpers for Step 2: loading the event log, evaluating and drawing Petri nets.

Two versions of the log are used:
    raw    - the log as given (events without a timestamp cannot be used and are dropped)
    clean  - the same log without the cases that Step 1 flagged as having timestamp errors
The clean log is NOT a correction (that is Step 5); it is a reference to show how
the errors change each discovered model.
"""
import json
import os
import warnings
from pathlib import Path

import pandas as pd
import pm4py
from pm4py.algo.evaluation.generalization import algorithm as generalization_eval
from pm4py.algo.evaluation.simplicity import algorithm as simplicity_eval

warnings.filterwarnings("ignore")

GRAPHVIZ_BIN = r"C:\Program Files\Graphviz\bin"
if Path(GRAPHVIZ_BIN).exists() and GRAPHVIZ_BIN not in os.environ["PATH"]:
    os.environ["PATH"] += os.pathsep + GRAPHVIZ_BIN

CSV = "insurance_claims_log.csv"
ERRORS = "output/step1_errors.csv"
OUT = Path("output/step2")


def load_log(version="raw", csv=CSV, errors=ERRORS):
    df = pd.read_csv(csv, dtype={"CaseID": str})
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], format="mixed", errors="coerce")
    if version == "clean":
        bad_cases = pd.read_csv(errors)["case"].unique()
        df = df[~df["CaseID"].isin(bad_cases)]
    df = df.dropna(subset=["Timestamp"])
    return pm4py.format_dataframe(df, case_id="CaseID", activity_key="Activity", timestamp_key="Timestamp")


def evaluate(log, net, im, fm):
    fit = pm4py.fitness_token_based_replay(log, net, im, fm)
    prec = pm4py.precision_token_based_replay(log, net, im, fm)
    sound = pm4py.check_soundness(net, im, fm)[0]
    try:
        align_fit = pm4py.fitness_alignments(log, net, im, fm)["average_trace_fitness"]
    except Exception:
        align_fit = None  # alignments need an easy-sound net; alpha nets may not be
    return {
        "cases": log["case:concept:name"].nunique(),
        "events": len(log),
        "variants": len(pm4py.get_variants(log)),
        "places": len(net.places),
        "transitions": len(net.transitions),
        "silent_transitions": sum(1 for t in net.transitions if t.label is None),
        "arcs": len(net.arcs),
        "fitness_tbr_perc_fit_traces": round(fit["perc_fit_traces"], 2),
        "fitness_tbr_avg": round(fit["average_trace_fitness"], 4),
        "fitness_alignments": None if align_fit is None else round(align_fit, 4),
        "precision": round(prec, 4),
        "generalization": round(generalization_eval.apply(log, net, im, fm), 4),
        "simplicity": round(simplicity_eval.apply(net), 4),
        "sound": bool(sound),
    }


def save_results(miner, version, log, net, im, fm):
    OUT.mkdir(parents=True, exist_ok=True)
    png = OUT / f"{miner}_{version}.png"
    pm4py.save_vis_petri_net(net, im, fm, str(png), rankdir="LR")
    pm4py.write_pnml(net, im, fm, str(OUT / f"{miner}_{version}.pnml"))
    metrics = evaluate(log, net, im, fm)
    (OUT / f"{miner}_{version}.json").write_text(json.dumps(metrics, indent=2))
    print(f"\n[{miner} | {version}] -> {png}")
    for k, v in metrics.items():
        print(f"  {k:30s} {v}")
    return metrics
