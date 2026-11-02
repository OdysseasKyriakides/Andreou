---
tags: [bpm, step]
status: done
---

# Step 4 - Trace Summary + Enhancement ✅

Goal: case ID → LLM narrative with users, waits, costs, bottleneck.

Code: `trace_facts`, `summarize_trace`, `check_numbers` in [[assistant.py]]; tab in [[app.py]].
Design: code computes facts (waits vs median, costs vs average $1,414, bottleneck rule from [[Design - Bottleneck threshold]], Step 1 issues from the [[Ground Truth]]); the LLM only writes the text; [[Hallucination Check]] verifies every number.

Test traces: Case_1 (clean), Case_5 (type C), Case_13 (type B), Case_77 (type A) - see [[Error Types A-D]].
8 summaries ([[BPM - Gemini|Gemini]] + [[BPM - Groq|Groq]]), 0 hallucinations. Results → [[Step 3-4 Outputs]].

Prev ← [[Step 3 - LLM Assistant GUI]] · Next → [[Step 5 - Timestamp Correction]]
