---
tags: [bpm, output, step2]
---

# Step 2 Outputs (`output/step2/`)

- `{alpha,heuristic,inductive}_{raw,clean}.{png,pnml,json}` - Petri nets + metrics ([[pm_common.py]])
- `comparison.csv` - [[Process Mining Metrics]] side by side
- `variants.csv` - 5 variants linked to [[Error Types A-D]]
- `output/Step2_Process_Discovery.docx` ([[step2_compare.py]])

| | alpha raw | heuristic raw | inductive raw | clean (all) |
|---|---|---|---|---|
| Fit traces % | 0 | 84 | 100 | 100 |
| Fitness (TBR) | 0.935 | 0.976 | 1.0 | 1.0 |
| Precision | 1.0 | 1.0 | 0.729 | 1.0 |
| Sound | ✗ | ✓ | ✓ | ✓ |

[[Step 2 - Process Discovery]]
