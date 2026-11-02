---
tags: [bpm, output, step3, step4]
---

# Step 3-4 Outputs (`output/step3_4/`)

From [[step34_run_both.py]]:
- `results.md` - full answers, code and summaries
- `summary.csv` - per call: ok, retries, seconds, tokens, answer, numbers/verified
- `Gemini_q1-5.html`, `Groq_q2-5.html` - plotly charts (Groq gave no chart for Q1)

⚠️ Stale - from before [[Design - Bottleneck threshold]]; re-run after [[Decision - Gemini Quota]].

Timing: [[BPM - Gemini|Gemini]] 7-31 s, [[BPM - Groq|Groq]] 1.2-2.8 s. All 8 trace summaries passed the [[Hallucination Check]].
[[Step 3 - LLM Assistant GUI]] · [[Step 4 - Trace Summary]]
