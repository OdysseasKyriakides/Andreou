---
tags: [bpm, step]
status: done
---

# Step 1 - Timestamp Errors ✅

Goal: find timestamp errors in the [[Insurance Claims Log]] **with code** ([[Rule - Steps 1-2 Code Only]]).

Code: [[step1_timestamp_errors.py]] (detection) → [[step1_report_docx.py]] (Word report).
Checks: missing/unparseable, format consistency, out of range, file order, precedence (≥80% support), duplicates, duration outliers (3σ), day/month swap suggestion, XES vs CSV.

Result: **22 suspicious events in 22 cases** → [[Ground Truth]], classified as [[Error Types A-D]].
Outputs → [[Step 1 Outputs]]. Commit `a9d57ab` "Step1 Completed" ([[Timeline]]).

Prev ← [[Step 0 - Setup]] · Next → [[Step 2 - Process Discovery]]
