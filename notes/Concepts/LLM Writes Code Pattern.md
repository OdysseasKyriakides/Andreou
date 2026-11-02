---
tags: [bpm, concept, design]
---

# LLM Writes Code Pattern

Core design of the app: the LLM **never answers with numbers directly**. It writes pandas code; the app runs it on the real data in a sandbox ([[safe_exec.py]]) and shows the code in the GUI.

- [[Step 3 - LLM Assistant GUI]]: question → code → table/plotly chart (`ask_log` in [[assistant.py]])
- [[Step 4 - Trace Summary]]: variant - code computes the facts, LLM only writes the narrative, then [[Hallucination Check]]
- [[Step 5 - Timestamp Correction]]: planned - each LLM writes correction code for each method → 4 corrected logs

Why: numbers can't be invented; satisfies the spirit of [[Rule - Steps 1-2 Code Only]].
