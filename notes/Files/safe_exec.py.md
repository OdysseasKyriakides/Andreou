---
tags: [bpm, file, code, app, security]
---

# `safe_exec.py`


Sandbox for LLM-generated pandas code ([[LLM Writes Code Pattern]]): `extract_code`, AST `check_code` blocks imports, file access, dunders and names like eval/exec/open/getattr; `run_code` exposes only `events`, `cases`, pd, np, px.
Used by [[assistant.py]].
