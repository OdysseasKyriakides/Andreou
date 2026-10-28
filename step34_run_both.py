"""
Runs Steps 3 and 4 with BOTH LLMs on a fixed set of questions and traces, and saves
the answers, generated code, time and tokens - evidence for the report and input for Steps 6-7.

Usage: python step34_run_both.py
Outputs: output/step3_4/results.md, output/step3_4/summary.csv, output/step3_4/<provider>_q<n>.html (charts)
"""
import tomllib
from pathlib import Path

import pandas as pd

from assistant import EXAMPLES_STEP3, ask_log, summarize_trace
from llm import PROVIDERS
from log_data import build_cases, load_events

TRACES = ["Case_1", "Case_5", "Case_13", "Case_77"]  # normal, shifted (C), truncated (B), missing (A)
OUT = Path("output/step3_4")
OUT.mkdir(parents=True, exist_ok=True)

keys = tomllib.load(open(".streamlit/secrets.toml", "rb"))
events = load_events()
cases = build_cases(events)
rows, md = [], ["# Steps 3 & 4 - results with both LLMs\n"]

md.append("## Step 3 - Questions on the log\n")
for i, q in enumerate(EXAMPLES_STEP3, 1):
    md.append(f"### Q{i}. {q}\n")
    for p, cfg in PROVIDERS.items():
        model = cfg["default_model"]
        print(f"[3] Q{i} {p} ...", flush=True)
        try:
            r = ask_log(p, model, keys[cfg["key_name"]], q, events, cases)
        except Exception as e:
            r = {"error": f"API: {e}", "answer": "", "result": None, "fig": None, "code": "",
                 "retries": 0, "seconds": 0, "input_tokens": 0, "output_tokens": 0}
        if r["fig"] is not None:
            r["fig"].write_html(OUT / f"{p}_q{i}.html", include_plotlyjs="cdn")
        table = r["result"].head(10).to_markdown(index=False) if isinstance(r["result"], pd.DataFrame) else str(r["result"])
        md += [f"**{p} ({model})** - {r['seconds']:.1f} s, {r['input_tokens']}+{r['output_tokens']} tokens"
               + (f", retries: {r['retries']}" if r["retries"] else ""),
               f"\n> {r['answer'] or r['error']}\n", table, "",
               "<details><summary>code</summary>\n\n```python\n" + r["code"] + "\n```\n</details>\n"]
        rows.append({"step": 3, "item": f"Q{i}", "provider": p, "model": model, "ok": r["error"] is None,
                     "retries": r["retries"], "seconds": round(r["seconds"], 2),
                     "input_tokens": r["input_tokens"], "output_tokens": r["output_tokens"],
                     "chart": r["fig"] is not None, "answer": r["answer"] or r["error"]})

md.append("## Step 4 - Trace summaries\n")
for case in TRACES:
    md.append(f"### {case}\n")
    for p, cfg in PROVIDERS.items():
        model = cfg["default_model"]
        print(f"[4] {case} {p} ...", flush=True)
        try:
            r = summarize_trace(p, model, keys[cfg["key_name"]], case, events, cases)
        except Exception as e:
            r = {"text": f"API error: {e}", "check": {"numbers": 0, "verified": 0, "unverified": []},
                 "seconds": 0, "input_tokens": 0, "output_tokens": 0}
        chk = r["check"]
        md += [f"**{p} ({model})** - {r['seconds']:.1f} s, {r['input_tokens']}+{r['output_tokens']} tokens, "
               f"numbers verified {chk['verified']}/{chk['numbers']}"
               + (f", NOT in facts: {chk['unverified']}" if chk["unverified"] else ""),
               f"\n> {r['text']}\n"]
        rows.append({"step": 4, "item": case, "provider": p, "model": model, "ok": True, "retries": 0,
                     "seconds": round(r["seconds"], 2), "input_tokens": r["input_tokens"],
                     "output_tokens": r["output_tokens"], "numbers": chk["numbers"],
                     "numbers_verified": chk["verified"], "answer": r["text"]})

(OUT / "results.md").write_text("\n".join(md), encoding="utf-8")
summary = pd.DataFrame(rows)
summary.to_csv(OUT / "summary.csv", index=False)
print(summary.drop(columns="answer").to_string())
print(f"\nSaved {OUT / 'results.md'} and {OUT / 'summary.csv'}")
