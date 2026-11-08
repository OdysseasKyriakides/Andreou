# HANDOFF - BPM-GenAI Assignment (ΜΗΥΠ 521)

Last session: **2026-11-08** · Deadline: **30/11/2026** (report on Moodle + public web link to the app)

The assignment brief is `Εργασία ΒΡΜ 2026.pdf`. The full task plan is in `PLAN.md`.
The rule from the brief: Steps 1-2 must be done **with code (PM4PY), not LLM answers**.

---

## Status

| Step | Task | Status |
|---|---|---|
| 0 | Setup (Python, libraries, Graphviz) | ✅ Done |
| 1 | Find timestamp errors with code | ✅ Done + Word file |
| 2 | Alpha / heuristic / inductive miner + comparison | ✅ Done + Word file |
| 3 | LLM assistant GUI (questions → tables/charts) | ✅ Done. Needs a re-run with Gemma + Qwen (`step34_run_both.py`) |
| 4 | Trace summary + enhancement | ✅ Done. Same re-run as Step 3 |
| 5 | Fix timestamps: 2 LLMs × (statistical, ML) + short literature review | ⏳ Code + app tab done; **final batch run pending**; literature review not written |
| 6 | 2×2 error tables (Accuracy, Precision, Recall, F1, hallucination...) | ⬜ Not started |
| 7 | Time (s) and cost (tokens) comparison | ⬜ Not started (data is already being logged) |
| 8 | Word/PDF report + deploy app online | ⬜ Not started |

---

## Environment

- Python 3.12.10 at `%LOCALAPPDATA%\Programs\Python\Python312\python.exe`
  (the plain `python` command may open the Microsoft Store in old terminals; open a new terminal or use the full path)
- Libraries: see `requirements.txt` (pandas, pm4py, python-docx, streamlit, plotly, requests, scikit-learn, tabulate)
  (reinstalled on 2026-11-08: they had disappeared from Python 3.12). The bare `python` resolves to a Store 3.13 without them.
- Ollama 0.40.14, models `bpm-gemma4` and `bpm-qwen` (see below). GPU: AMD RX 9070 XT 16 GB, RAM 31 GB.
- Graphviz: `C:\Program Files\Graphviz\bin` (added to PATH in code by `pm_common.py`)
- No API keys anymore (Gemini and Groq dropped on 2026-11-08). The old Gemini/Groq keys were pasted in a chat: revoke them.

## Data

- `insurance_claims_log.csv` and `insurance_claims_log.xes`: 100 cases, 500 events. The two files are **identical** (0 timestamp differences)
- Columns: `CaseID, Activity, Timestamp, User, Cost`
- 5 activities: Register Claim → Verify Documents → Evaluate Claim → Approve Claim → Close Claim
- Users: User_A … User_E. Period: 2026-09-01 … 2026-12-09 (one case per day)

---

## Step 1 - Timestamp errors (code: `step1_timestamp_errors.py`)

22 suspicious events in 22 cases. **This list is the ground truth for Steps 5-6.**

| Type | What | Cases |
|---|---|---|
| A | Missing timestamp (empty) | 28 (Verify), 34, 70, 84 (Evaluate), 77 (Register) |
| B | Truncated timestamp, hour only, e.g. `2026-09-13T16` | 13, 16, 20, 75, 93 |
| C | Approve Claim exactly **15 min earlier** than the Evaluate written before it (systematic shift) | 5, 6, 31, 60, 81 |
| D | Approve before Evaluate in both file order and time (swapped timestamps or a real deviation; undecidable from the data alone) | 4, 15, 29, 32, 36, 82, 95 |

Outputs: `output/step1_errors.csv`, `output/step1_summary.txt`, `output/Step1_Timestamp_Errors.docx` (built by `step1_report_docx.py`)

## Step 2 - Discovery (code: `step2_alpha_miner.py`, `step2_heuristic_miner.py`, `step2_inductive_miner.py`, `step2_compare.py`, shared `pm_common.py`)

Each miner runs on **raw** (as given) and **clean** (without the 22 Step 1 cases, as a reference, not a correction).

- Clean log → all three give the same perfect sequence (all metrics 1.0) ⇒ all differences come from the errors
- Raw log has 5 variants: 83 normal, 12 Approve↔Evaluate (C+D), 3 missing Evaluate (A), 1 missing Verify (A), 1 missing Register (A)
- Alpha: makes Approve ∥ Evaluate parallel, **unsound**, 0% traces fit
- Heuristic: most robust, sound, 84% traces fit
- Inductive: sound, fitness 1.0, but over-generalises (precision 0.73)

Outputs: `output/step2/` (PNG + PNML + JSON per miner/version, `comparison.csv`, `variants.csv`), `output/Step2_Process_Discovery.docx`
Note: the comment paragraphs in `step2_compare.py` (`COMMENTS`) were written by Claude. Rewrite them in your own words if needed.

## Steps 3, 4, 5 - App (`app.py`, run: `python -m streamlit run app.py`)

| File | Role |
|---|---|
| `app.py` | Streamlit GUI, tabs: Step 3, Step 4, Step 5. Sidebar: run with Both / Gemma / Qwen |
| `assistant.py` | Step 3 `ask_log()` and Step 4 `summarize_trace()`, `trace_facts()`, `check_numbers()` (hallucination check) |
| `llm.py` | Ollama client for both LLMs; logs every call to `output/llm_usage.csv` (seconds **without** model load time, load_seconds, tokens) for Step 7; `unload()` frees the GPU |
| `safe_exec.py` | Sandbox for LLM code: no files/dunders/eval; imports only pandas, numpy, sklearn, datetime, math, statistics. `run_fix_code()` for Step 5, `describe_error()` adds the failing line to retry messages |
| `log_data.py` | Builds `events` and `cases` (`load_events` also accepts a DataFrame, used for synthetic logs) |
| `step34_run_both.py` | Batch: 5 questions + 4 traces on both LLMs → `output/step3_4/` |
| `step5_fix.py` | Step 5 prompts, `generate_fix()` (LLM writes detect+correct code, up to 3 retries), `inject_errors()`, `evaluate_fix()` |
| `step5_run_both.py` | Batch: 2 LLMs × 2 methods → `output/step5/` (code, corrected CSVs, `metrics.csv`, `synthetic.csv`, `results.md`). Options `--only Gemma|Qwen`, `--method Statistical|ML` |

- Step 3 design: the LLM **writes pandas code**, the app runs it on the real data → numbers are never invented; the code is shown in the GUI.
- Step 4 design: code computes the facts; the LLM only writes the narrative; every number in it is verified against the facts.

**LLMs in use** (2026-11-08: Gemini and Groq dropped, the user wants only local Ollama models)

| Name | Ollama model | Base | Notes |
|---|---|---|---|
| Gemma | `bpm-gemma4` (`models/gemma.Modelfile`) | `gemma4:12b` (Google, 8 GB) | called with `think: false` (thinking ran ~15.8k tokens / 220 s, empty answer). 4-8 s per Step 3 answer |
| Qwen | `bpm-qwen` (`models/qwen.Modelfile`) | `qwen2.5-coder:14b` (Alibaba, 9 GB, 12 GB loaded) | code-specialised, different family from Gemma |

Both: temperature 0, top_k 1, seed 42, num_ctx 16384. Rebuild: `ollama create bpm-gemma4 -f models/gemma.Modelfile` (same for qwen).
The two do not fit in VRAM together → the batches call `unload()` after each model, else it spills to CPU (one Qwen run took 358 s).

## Step 5 design

- Each LLM writes code that **detects and corrects** (prompt: `SYSTEM_STEP5` + `METHOD_PROMPTS` in `step5_fix.py`).
  The prompt gives the normative order and the 3 error kinds (missing, hour only, out of order) but **not** which cases.
  Output contract: `fixed` = events + `is_error` + `timestamp_fixed`, and `answer`.
- Statistical: median waiting time per transition. ML: one sklearn regressor predicting `waiting_min`.
- Scoring (`evaluate_fix`):
  - Real log: case-level detection vs the 22 Step 1 cases → accuracy, precision, recall, F1; % claims in normative order after the fix
  - Synthetic: 5 seeds, each injects 20 errors (5 per type A/B/C/D, D swaps 2 events) into error-free claims, so the
    truth is known → event-level P/R/F1, MAE, median AE, % within 60 min, % order restored, MAE per type
  - Hallucination / invalid output: code failed after retries, NaT left, silent changes, numbers in `answer` not matching
  - `fix_runtime_s` = runtime of the generated code (Step 7)
- Hand-written reference fix (not an LLM, sanity check only): real F1 0.81, synthetic F1 0.89, MAE 44 min.

**Run history (2026-11-08)**
1. First run: only Gemma/Statistical worked (real F1 0.81, but synthetic MAE 5,363 min: A/B repairs days off).
   Gemma/ML predicted a date in 2037; Qwen kept writing `import` (blocked) → failed.
2. Fixes (same for both LLMs): whitelisted imports, pandas tips in the prompt, failing line in the retry message,
   3 retries, unload between models, load time excluded from seconds.
3. Second run was **killed by Claude Code because the PC ran low on memory** (during Gemma/ML). Nothing saved.
   `output/step5/` still holds the first run's files (outdated; they are not committed).

## Next steps

1. Close heavy programs (memory), then start a fresh usage log (move `output/llm_usage.csv` aside, it has test runs) and run:
   `step5_run_both.py` (~15-20 min) and `step34_run_both.py`. Use the Python 3.12 path.
2. Look at the Step 5 results; if a combination still fails, that is a valid finding (report it), don't over-tune the prompt.
3. Write the short literature review for Step 5. Candidate references: Suriadi et al. 2017 (event log imperfection
   patterns, Information Systems 64); Dixit et al. 2018 (event ordering imperfections, CAiSE); Fischer et al. 2020
   (timestamp quality, BPM); Rogge-Solti et al. 2013 (repairing event logs); Breiman 2001 (random forests);
   Friedman 2001 (gradient boosting); Verenich et al. 2019 (remaining time prediction survey, ACM TIST). Verify each before citing.
4. **Step 6**: script that builds the 2×2 tables (rows Statistical/ML, columns Gemma/Qwen) from `output/step5/metrics.csv`.
5. **Step 7**: time/tokens from `output/llm_usage.csv` + `fix_runtime_s`. Local models: cost = tokens and seconds, $0.
6. Optional: re-run Step 2 miners on the corrected logs (`output/step5/*_corrected.csv`).
7. **Step 8**: report + public link. ⚠️ Streamlit Cloud cannot reach Ollama on this PC. Options: tunnel to this PC
   during grading, a cloud host with a GPU, or deploy a read-only version that shows the recorded results. **Decide with the user.**
