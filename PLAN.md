# BPM-GenAI Assignment Plan (ΜΗΥΠ 521, due 30/11/2026)

Dataset: 100 insurance-claim cases, given as CSV and XES. Put both in `data/`.

| # | Task | How | Output |
|---|------|-----|--------|
| 0 | Setup | Install Python 3.11+, `pip install -r requirements.txt` | working env |
| 1 | Find timestamp errors (code only, no LLM) | `step1_timestamp_errors.py` (pandas + PM4PY) | `output/step1_errors.csv`, summary and explanations for the report |
| 2 | α-miner, heuristic miner, inductive miner Petri nets | `step2_discovery.py` (PM4PY) on the raw log and on the corrected log | 3 or 6 Petri-net PNGs, fitness/precision table, comments on how the errors affect each model |
| 5 | Fix timestamps with 2 LLMs × 2 methods (statistical / ML) | GUI; LLM A + LLM B each generate the correction code; we run it | corrected logs, short literature review. Can be done before step 2 if the miners fail |
| 3 | LLM assistant GUI (questions → tables/charts) | Streamlit + LLM API; the LLM writes pandas queries that run on the log | web app |
| 4 | Trace summary + enhancement | same app: case ID → LLM summary with durations, cost, bottleneck | app tab |
| 6 | 2×2 error tables (rows: Solution A/B, columns: Model A/B) | compare corrections against the Step 1 ground truth: Accuracy, Precision, Recall, F1, MAE (hours), hallucination rate | tables |
| 7 | Time (s) and cost (tokens) comparison | log timing and token usage per run | table |
| 8 | Word/PDF report + public web link (Streamlit Community Cloud / HF Spaces) | — | report on Moodle |

Key idea: the Step 1 error list (found with code) becomes the **ground truth** for evaluating Steps 5–6.
