---
tags: [bpm, concept]
---

# Ground Truth

The list of **22 suspicious events in 22 cases** found by code in [[Step 1 - Timestamp Errors]] (`output/step1_errors.csv`, see [[Step 1 Outputs]]).

Used for:
- [[Raw vs Clean Log]] in [[Step 2 - Process Discovery]] (clean = without these 22 cases)
- Data-quality flags in [[Step 4 - Trace Summary]] (`_load_step1_issues` in [[assistant.py]])
- Evaluating corrections in [[Step 5 - Timestamp Correction]] and [[Step 6 - Error Tables]] (Accuracy / Precision / Recall / F1)

Breakdown → [[Error Types A-D]].
Idea for Step 5: also inject synthetic errors into clean cases where the true value is known, to measure MAE.
