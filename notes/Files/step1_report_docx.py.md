---
tags: [bpm, file, code, step1]
---

# `step1_report_docx.py`


Builds `Step1_Timestamp_Errors.docx` ([[Step 1 Outputs]]) from the errors CSV.
`classify()` assigns [[Error Types A-D]]; `explain()` writes a per-event explanation; `add_table`/`shade` helpers.
Reused by [[step2_compare.py]] (imports `TYPES`, `add_table`, `classify`).
