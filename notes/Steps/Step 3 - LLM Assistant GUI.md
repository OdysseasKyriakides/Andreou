---
tags: [bpm, step]
status: done
---

# Step 3 - LLM Assistant GUI ✅

Goal: natural-language questions about the log → tables/charts.

Code: [[app.py]] (Streamlit tab) → `ask_log` in [[assistant.py]] → [[llm.py]] → [[safe_exec.py]], data from [[log_data.py]].
Design: [[LLM Writes Code Pattern]]. Run with Both / [[BPM - Gemini|Gemini]] / [[BPM - Groq|Groq]] from the sidebar.

5 benchmark questions (batch in [[step34_run_both.py]]): Q1 User_A claims > $400 (61), Q2 longest waiting activity, Q3 cost per user (User_C top, $32,838), Q4 variants, Q5 average duration (4.98 h) per week.
Both LLMs gave matching numbers on Q1, Q3, Q4, Q5. Q2 differs (Gemini: Evaluate, Groq: Close) → worth re-checking after the re-run.
Results → [[Step 3-4 Outputs]]. Commit `55d1d8c`.

Prev ← [[Step 2 - Process Discovery]] · Next → [[Step 4 - Trace Summary]]
