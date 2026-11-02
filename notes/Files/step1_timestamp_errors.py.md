---
tags: [bpm, file, code, step1]
---

# `step1_timestamp_errors.py`


Detects timestamp errors - [[Step 1 - Timestamp Errors]]. Pure pandas + PM4PY ([[Rule - Steps 1-2 Code Only]]).
Reads [[Insurance Claims Log]] (auto-guesses column names).

Checks: `check_missing_or_unparseable`, `check_format_consistency`, `check_out_of_range`, `check_file_order`, `check_precedence` (min support 0.8, ≥10 cases), `check_duplicates`, `check_duration_outliers` (k=3), `suggest_day_month_swap`, `check_xes_vs_csv`, `pm4py_overview`.
Writes `step1_errors.csv`, `step1_summary.txt` → [[Step 1 Outputs]] → becomes the [[Ground Truth]].
