---
tags: [bpm, concept]
---

# Process Mining Metrics

Computed by `evaluate()` in [[pm_common.py]] for each miner in [[Step 2 - Process Discovery]]:
- **Fitness** (token replay + alignments) - can the model replay the log?
- **Precision** - does the model allow only observed behaviour?
- **Generalization**, **Simplicity**
- **Soundness** (workflow net check)
- Structure: places, transitions, silent τ transitions, arcs

Comparison table → [[Step 2 Outputs]]. Different from the *classification* metrics (Accuracy/Precision/Recall/F1) used in [[Step 6 - Error Tables]].
