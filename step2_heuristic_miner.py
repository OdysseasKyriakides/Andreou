"""
Step 2b - Heuristic miner.

Uses frequencies: an arc a -> b is kept only if its dependency measure
(|a>b| - |b>a|) / (|a>b| + |b>a| + 1) is above the threshold, so rare
(possibly wrong) orderings can be filtered out.

Usage: python step2_heuristic_miner.py [--threshold 0.5]
"""
import argparse

import pm4py

from pm_common import load_log, save_results

ap = argparse.ArgumentParser()
ap.add_argument("--threshold", type=float, default=0.5)
args = ap.parse_args()

for version in ["raw", "clean"]:
    log = load_log(version)
    net, im, fm = pm4py.discover_petri_net_heuristics(log, dependency_threshold=args.threshold)
    save_results("heuristic", version, log, net, im, fm)
