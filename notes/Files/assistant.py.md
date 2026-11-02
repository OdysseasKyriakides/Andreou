---
tags: [bpm, file, code, app]
---

# `assistant.py`


LLM logic for the app:
- `ask_log()` - Step 3, [[LLM Writes Code Pattern]] (`EXAMPLES_STEP3` questions)
- `trace_facts()`, `summarize_trace()` - Step 4 ([[Step 4 - Trace Summary]], [[Design - Bottleneck threshold]])
- `check_numbers()` - [[Hallucination Check]]
- `_load_step1_issues()` - reads the [[Ground Truth]]

Uses [[llm.py]], [[safe_exec.py]], [[log_data.py]].
