---
tags: [bpm, data]
---

# Insurance Claims Log

Files: `insurance_claims_log.csv` and `insurance_claims_log.xes` (committed in `a9d57ab`). The two are **identical** (0 timestamp differences, checked by `check_xes_vs_csv` in [[step1_timestamp_errors.py]]).

- 100 cases, 500 events (495 with a parseable timestamp)
- Columns: `CaseID, Activity, Timestamp, User, Cost`
- 5 activities: Register Claim → Verify Documents → Evaluate Claim → Approve Claim → Close Claim
- Users User_A … User_E; period 2026-09-01 … 2026-12-09 (one case per day)
- Case duration: min 2.6 h, median 5.0 h, max 7.1 h
- Contains 22 deliberately broken events → [[Error Types A-D]], [[Ground Truth]]

Loaded by: [[pm_common.py]] (PM4PY), [[log_data.py]] (app), [[step1_timestamp_errors.py]].
