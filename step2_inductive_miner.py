"""
Step 2c - Inductive miner.

Recursively splits the log into a process tree (sequence, choice, parallel, loop)
and converts it to a Petri net. The result is always sound. With noise_threshold=0
every observed behaviour must be replayable (perfect fitness); higher values (IMf)
ignore infrequent behaviour.

Usage: python step2_inductive_miner.py [--noise 0.0]
"""
import argparse

import pm4py

from pm_common import load_log, save_results

ap = argparse.ArgumentParser()
ap.add_argument("--noise", type=float, default=0.0)
args = ap.parse_args()

for version in ["raw", "clean"]:
    log = load_log(version)
    net, im, fm = pm4py.discover_petri_net_inductive(log, noise_threshold=args.noise)
    save_results("inductive", version, log, net, im, fm)
