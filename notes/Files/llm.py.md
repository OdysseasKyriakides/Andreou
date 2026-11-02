---
tags: [bpm, file, code, app, llm]
---

# `llm.py`


REST calls to [[BPM - Gemini|Gemini]] and [[BPM - Groq|Groq]] (`PROVIDERS`, `chat()`); retries on 429/503.
Logs every call (seconds, tokens, step, provider) to [[llm_usage.csv]] - the data source for [[Step 7 - Time and Cost]].
