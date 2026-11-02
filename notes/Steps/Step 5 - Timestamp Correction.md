---
tags: [bpm, step, todo]
status: next
---

# Step 5 - Timestamp Correction ⏳ NEXT

Blocked on [[Decision - Gemini Quota]].

Plan:
- **Solution A - statistical**: impute/correct with the median waiting time per transition (Evaluate→Approve etc.)
- **Solution B - ML**: regression (gradient boosting / random forest) predicting waiting time from activity, previous activity, user, cost, weekday/hour
- Each LLM ([[BPM - Gemini|Gemini]], [[BPM - Groq|Groq]]) generates the code for each solution → **4 corrected logs** ([[LLM Writes Code Pattern]])
- New tab in [[app.py]] (placeholder exists) + batch script
- Short literature review for both methods (for the report)
- Keep original values of known-good events; inject synthetic errors into clean cases to measure MAE ([[Ground Truth]])
- Targets: [[Error Types A-D]] (A impute, B complete the minutes, C undo the 15-min shift, D decide swap vs deviation)

Prev ← [[Step 4 - Trace Summary]] · Next → [[Step 6 - Error Tables]]
