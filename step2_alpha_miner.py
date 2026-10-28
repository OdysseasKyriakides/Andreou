"""
Step 2a - Alpha miner.

Builds the Petri net only from the directly-follows relations (a > b) in the log.
It has no noise handling: one wrong order in one case is enough to change the model.

Usage: python step2_alpha_miner.py
"""
import pm4py

from pm_common import load_log, save_results

for version in ["raw", "clean"]:
    log = load_log(version)
    net, im, fm = pm4py.discover_petri_net_alpha(log)
    save_results("alpha", version, log, net, im, fm)
