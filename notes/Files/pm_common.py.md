---
tags: [bpm, file, code, step2]
---

# `pm_common.py`


Shared helpers for [[Step 2 - Process Discovery]]:
- Adds Graphviz to PATH ([[Step 0 - Setup]])
- `load_log(version)` - raw or clean ([[Raw vs Clean Log]]) using the [[Ground Truth]] errors CSV
- `evaluate()` - [[Process Mining Metrics]]
- `save_results()` - PNG + PNML + JSON per miner/version → [[Step 2 Outputs]]

Used by [[step2_alpha_miner.py]], [[step2_heuristic_miner.py]], [[step2_inductive_miner.py]], [[step2_compare.py]].
