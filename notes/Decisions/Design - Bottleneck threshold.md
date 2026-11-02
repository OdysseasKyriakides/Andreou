---
tags: [bpm, decision]
---

# Design - Bottleneck threshold & variant_by_time

Fixes made after the first [[step34_run_both.py]] run (so [[Step 3-4 Outputs]] predate them):
- A stage is a **bottleneck** only if its wait is ≥ **1.2× the median** wait of that transition (before, Case_1 flagged a 0.9× stage) - in `trace_facts` ([[assistant.py]])
- [[log_data.py]] now has both `variant` (file order) and `variant_by_time` (process-mining definition). The two disagree on Q4 (2 vs 5 variants) because of [[Error Types A-D]]
- [[Hallucination Check]] improved
