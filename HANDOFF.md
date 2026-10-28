# HANDOFF - BPM-GenAI Assignment (ΜΗΥΠ 521)

Last session: **2026-10-28** · Deadline: **30/11/2026** (report on Moodle + public web link to the app)

The assignment brief is `Εργασία ΒΡΜ 2026.pdf`. The full task plan is in `PLAN.md`.
The rule from the brief: Steps 1-2 must be done **with code (PM4PY), not LLM answers**.

---

## Status

| Step | Task | Status |
|---|---|---|
| 0 | Setup (Python, libraries, Graphviz) | ✅ Done |
| 1 | Find timestamp errors with code | ✅ Done + Word file |
| 2 | Alpha / heuristic / inductive miner + comparison | ✅ Done + Word file |
| 3 | LLM assistant GUI (questions → tables/charts) | ✅ Done, works with both LLMs |
| 4 | Trace summary + enhancement | ✅ Done, works with both LLMs |
| 5 | Fix timestamps: 2 LLMs × (statistical, ML) + short literature review | ⏳ **NEXT**: blocked on Gemini quota decision |
| 6 | 2×2 error tables (Accuracy, Precision, Recall, F1, hallucination...) | ⬜ Not started |
| 7 | Time (s) and cost (tokens) comparison | ⬜ Not started (data is already being logged) |
| 8 | Word/PDF report + deploy app online | ⬜ Not started |

---

## Environment

- Python 3.12.10 at `%LOCALAPPDATA%\Programs\Python\Python312\python.exe`
  (the plain `python` command may open the Microsoft Store in old terminals; open a new terminal or use the full path)
- Libraries: see `requirements.txt` (pandas, pm4py, python-docx, streamlit, plotly, requests; tabulate installed too)
- Graphviz: `C:\Program Files\Graphviz\bin` (added to PATH in code by `pm_common.py`)
- API keys: `.streamlit/secrets.toml` (git-ignored, **never commit**). Template: `.streamlit/secrets.toml.example`
  - Keys were pasted in a chat; consider creating new ones when the project is done.

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

## Steps 3 & 4 - App (`app.py`, run: `python -m streamlit run app.py`)

| File | Role |
|---|---|
| `app.py` | Streamlit GUI, tabs: Step 3, Step 4, Step 5 (placeholder). Sidebar: run with Both / Gemini / Groq |
| `assistant.py` | Step 3 `ask_log()` and Step 4 `summarize_trace()`, `trace_facts()`, `check_numbers()` (hallucination check) |
| `llm.py` | REST calls to Gemini and Groq, retries on 429/503, logs every call to `output/llm_usage.csv` (for Step 7) |
| `safe_exec.py` | Runs LLM-generated pandas code in a restricted sandbox (no imports/files/dunders) |
| `log_data.py` | Builds `events` and `cases` DataFrames + schema text for the LLM (`variant` = file order, `variant_by_time` = PM definition) |
| `step34_run_both.py` | Batch: 5 questions + 4 traces (Case_1, 5, 13, 77) on both LLMs → `output/step3_4/results.md`, `summary.csv`, chart HTMLs |

- Step 3 design: the LLM **writes pandas code**, the app runs it on the real data → numbers are never invented; the code is shown in the GUI.
- Step 4 design: code computes the facts (users, waits vs median, costs vs average, bottleneck ≥1.2× median, Step 1 issues); the LLM only writes the narrative; every number in it is verified against the facts.

**LLMs in use**

| Provider | Model | Notes |
|---|---|---|
| Gemini | `gemini-3.5-flash` | Free tier = **20 requests/day per model**. 7-31 s per answer, ~1,000-2,200 output tokens ("thinking") |
| Groq | `openai/gpt-oss-120b` | No Llama models available on Groq anymore. 1-3 s, ~300-1,100 output tokens |

Results so far: both LLMs answered all 5 questions correctly with matching numbers. All 8 trace summaries: every number verified, 0 hallucinations.

⚠️ `output/step3_4/results.md` is from the run **before** the last fixes (variant_by_time, bottleneck threshold, checker). Re-run `python step34_run_both.py` once the Gemini quota has reset (it uses 18 Gemini calls, almost the full daily 20).

---

## Open decision (ask the user first)

Gemini's free quota (20/day/model) is too small for Step 5. Options:
1. Use `gemini-3.5-flash-lite` (separate quota, confirmed working, slightly weaker), or
2. Enable billing in Google AI Studio (probably well under $1 total).

Other Gemini models seen on 2026-10-28: `gemini-3.8-flash` and `gemini-3.7-flash` were overloaded (503); `gemini-3.6-flash` worked.

## Next steps

1. Decide the Gemini option above, then re-run `step34_run_both.py`.
2. **Step 5** (new tab in `app.py` + batch script):
   - Solution A, statistical: e.g. impute/correct using the median waiting time per transition (Evaluate→Approve etc.)
   - Solution B, ML: e.g. a regression model (gradient boosting / random forest) that predicts the waiting time from activity, previous activity, user, cost, weekday/hour
   - Each LLM (Gemini, Groq) generates the correction code for each solution → 4 corrected logs. Same pattern as Step 3: the LLM writes code, the app runs it
   - Short literature review for both methods (for the report)
   - Keep the original values of known-good events to measure accuracy. Idea: also **inject synthetic errors** into clean cases, where the true value is known, to measure MAE
3. **Step 6**: 2×2 tables (rows: Solution A/B, columns: Gemini/Groq) per metric. Detection: Accuracy, Precision, Recall, F1 vs the Step 1 ground truth. Correction: MAE in minutes, % order restored. Hallucination: from `check_numbers` / invalid code.
4. **Step 7**: from `output/llm_usage.csv` (seconds, input/output tokens per call, per step/provider) + runtime of the correction methods.
5. Optional: re-run Step 2 miners on the 4 corrected logs to show the improvement.
6. **Step 8**: deploy the app on Streamlit Community Cloud (keys go in the Cloud "Secrets" setting, not the repo); put the link on the first page; build the report from the Step 1/2 Word files + Steps 3-7 results.
