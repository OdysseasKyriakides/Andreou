---
tags: [bpm, concept]
---

# Raw vs Clean Log

In [[Step 2 - Process Discovery]] every miner runs twice (`load_log(version)` in [[pm_common.py]]):
- **raw** - the log as given (100 cases, 495 events, 5 variants)
- **clean** - without the 22 [[Ground Truth]] cases (78 cases, 390 events, 1 variant). A *reference*, not a correction.

Finding: on the clean log [[Alpha Miner]], [[Heuristic Miner]] and [[Inductive Miner]] all produce the same perfect sequence (all metrics 1.0) ⇒ every difference in the raw models comes from the [[Error Types A-D]].

A third version - the **corrected** logs from [[Step 5 - Timestamp Correction]] - can optionally be re-mined later.
