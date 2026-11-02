---
tags: [bpm, concept]
---

# Error Types A-D

Classification of the [[Ground Truth]] errors (`classify` in [[step1_report_docx.py]]).

| Type | What | Cases |
|---|---|---|
| A | Missing timestamp | 28 (Verify), 34, 70, 84 (Evaluate), 77 (Register) |
| B | Truncated, hour only e.g. `2026-09-13T16` | 13, 16, 20, 75, 93 |
| C | Approve exactly **15 min earlier** than the Evaluate before it (systematic shift) | 5, 6, 31, 60, 81 |
| D | Approve before Evaluate in file order *and* time (swap or real deviation - undecidable) | 4, 15, 29, 32, 36, 82, 95 |

Detector checks (Step 1 summary): missing/unparseable 5 · format inconsistent 10 · earlier than previous event 5 · precedence violation 12. Day/month swap would fix 0 events.

Effect on discovery ([[Step 2 - Process Discovery]]): C+D → 12 cases with Approve↔Evaluate variant; A → 5 cases with a missing activity; B does not change the variant.
Examples in the app: Case_5 (C), Case_13 (B), Case_77 (A) in [[Step 4 - Trace Summary]].
