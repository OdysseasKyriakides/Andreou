---
tags: [bpm, concept, design]
---

# Hallucination Check

`check_numbers(text, facts)` in [[assistant.py]]: extracts every number from the LLM narrative and verifies it against the facts computed by `trace_facts`.
Columns `numbers` / `numbers_verified` in `summary.csv` ([[Step 3-4 Outputs]]).

Results (pre-fix run): all 8 summaries judged 0 hallucinations, though some rows show fewer verified than found (e.g. Case_13 Groq 11/8) - the checker was improved afterwards, re-run pending.
Will feed the hallucination metric in [[Step 6 - Error Tables]].
