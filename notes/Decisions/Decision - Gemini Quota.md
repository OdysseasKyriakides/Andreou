---
tags: [bpm, decision, open]
---

# Decision - Gemini Quota (OPEN)

**Problem:** [[BPM - Gemini|Gemini]] free tier = 20 requests/day/model - too small for [[Step 5 - Timestamp Correction]] (and a full [[step34_run_both.py]] re-run takes 18).

**Options**
1. Switch to `gemini-3.5-flash-lite` - separate quota, confirmed working, slightly weaker
2. Enable billing in Google AI Studio - probably well under $1 total

**Blocks:** re-running [[step34_run_both.py]] (results in [[Step 3-4 Outputs]] are stale) and starting Step 5.
Ask the user first.
