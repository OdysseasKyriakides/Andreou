---
tags: [bpm, llm]
---

# Gemini (Google)

Model in use: `gemini-3.5-flash`. Called via REST in [[llm.py]]; key in [[secrets.toml]].
- Free tier: **20 requests/day per model** → the blocker in [[Decision - Gemini Quota]]
- 7-31 s per answer, ~1,000-2,200 output tokens (thinking)
- Alternatives seen 2026-10-28: `gemini-3.5-flash-lite` works (separate quota); `3.6-flash` worked; `3.7`/`3.8-flash` overloaded (503)
- [[step34_run_both.py]] uses 18 Gemini calls per run

Compared with [[BPM - Groq|Groq]] in [[Step 3-4 Outputs]] and [[Step 7 - Time and Cost]].
