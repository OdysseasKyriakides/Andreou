---
tags: [bpm, step]
status: done
---

# Step 2 - Process Discovery ✅

Goal: discover Petri nets with three miners and compare how the errors affect each one.

Code: [[pm_common.py]] + [[step2_alpha_miner.py]], [[step2_heuristic_miner.py]], [[step2_inductive_miner.py]] → [[step2_compare.py]]. See [[Design - Step 2 split into separate miner scripts]].
Each miner runs on [[Raw vs Clean Log]]; metrics in [[Process Mining Metrics]].

Findings:
- Clean log → identical perfect sequence for all three
- Raw log 5 variants: 83 normal, 12 Approve↔Evaluate (C+D), 3 missing Evaluate, 1 missing Verify, 1 missing Register (A)
- [[Alpha Miner]] unsound, 0% fit · [[Heuristic Miner]] most robust, 84% fit · [[Inductive Miner]] fitness 1.0 but precision 0.73

Outputs → [[Step 2 Outputs]]. Commit `4e54f13` ([[Timeline]]).

Prev ← [[Step 1 - Timestamp Errors]] · Next → [[Step 3 - LLM Assistant GUI]]
