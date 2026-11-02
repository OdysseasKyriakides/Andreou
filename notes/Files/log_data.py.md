---
tags: [bpm, file, code, app]
---

# `log_data.py`


Builds the `events` and `cases` DataFrames from the [[Insurance Claims Log]] plus the `SCHEMA` text sent to the LLM.
`variant` = file order, `variant_by_time` = PM definition ([[Design - Bottleneck threshold]]).
Used by [[app.py]], [[assistant.py]].
