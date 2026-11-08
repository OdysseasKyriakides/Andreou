"""
Step 5 batch: each LLM (Gemma, Qwen) writes correction code for each method (Statistical, ML);
the code runs on the real log and on 5 logs with synthetic errors. Evidence for the report and
input for Step 6 (error tables) and Step 7 (time / tokens).

Usage:   python step5_run_both.py [--only Gemma|Qwen] [--method Statistical|ML]
Outputs: output/step5/<LLM>_<method>.py              generated code (final version)
         output/step5/<LLM>_<method>_corrected.csv   corrected real log (+ OriginalTimestamp, IsError)
         output/step5/metrics.csv                    one row per LLM x method (Step 6 / 7 input)
         output/step5/synthetic.csv                  per-seed synthetic results
         output/step5/results.md                     readable summary with code and answers
"""
import argparse
from pathlib import Path

import pandas as pd

from llm import PROVIDERS, unload
from log_data import load_events
from step5_fix import METHODS, changes_table, corrected_log, evaluate_fix, generate_fix

ap = argparse.ArgumentParser()
ap.add_argument("--only", choices=list(PROVIDERS))
ap.add_argument("--method", choices=METHODS)
args = ap.parse_args()

OUT = Path("output/step5")
OUT.mkdir(parents=True, exist_ok=True)
events = load_events()
metrics_path = OUT / "metrics.csv"
old = pd.read_csv(metrics_path) if metrics_path.exists() else pd.DataFrame(columns=["provider", "method"])
rows, syn_rows, md = [], [], ["# Step 5 - timestamp correction, 2 LLMs x 2 methods\n"]

for provider, cfg in PROVIDERS.items():
    if args.only and provider != args.only:
        continue
    for method in METHODS:
        if args.method and method != args.method:
            continue
        print(f"[5] {provider} / {method} ...", flush=True)
        r = generate_fix(provider, cfg["default_model"], method, events)
        name = f"{provider}_{method}"
        (OUT / f"{name}.py").write_text(r["code"], encoding="utf-8")
        row = {"provider": provider, "model": r["model"], "method": method, "ok": r["error"] is None,
               "retries": r["retries"], "llm_seconds": round(r["seconds"], 2),
               "input_tokens": r["input_tokens"], "output_tokens": r["output_tokens"],
               "error": r["error"] or "", "answer": r["answer"]}
        md += [f"## {provider} ({r['model']}) - {method}\n",
               f"{r['seconds']:.1f} s, {r['input_tokens']} + {r['output_tokens']} tokens, retries: {r['retries']}\n"]
        if r["errors"]:
            md.append("Errors during generation: " + "; ".join(f"`{e}`" for e in r["errors"]) + "\n")
        if r["error"]:
            md.append(f"**Failed:** `{r['error']}`\n")
        else:
            m, syn = evaluate_fix(r["code"], events, r["fixed"], r["answer"])
            row.update(m)
            syn.insert(0, "method", method)
            syn.insert(0, "provider", provider)
            syn_rows.append(syn)
            corrected_log(r["fixed"], events).to_csv(OUT / f"{name}_corrected.csv", index=False)
            ch = changes_table(r["fixed"], events)
            md += [f"**Answer:** {r['answer']}\n",
                   f"Real log - detection vs Step 1 (cases): precision {m['real_precision']:.2f}, "
                   f"recall {m['real_recall']:.2f}, F1 {m['real_f1']:.2f}; cases in normative order after fix "
                   f"{m['real_cases_in_order']:.0%}\n",
                   f"Synthetic errors - F1 {m['syn_f1']:.2f}, MAE {m['syn_mae_min']:.1f} min, median AE "
                   f"{m['syn_median_ae_min']:.1f} min, within 60 min {m['syn_within_60min']:.0%}, "
                   f"order restored {m['syn_order_restored']:.0%}\n",
                   f"Contract: NaT left {m['nat_left']}, silent changes {m['silent_changes']}, "
                   f"numbers in answer not matching {m['answer_unverified']}/{m['answer_numbers']}\n",
                   f"<details><summary>Corrected events ({len(ch)})</summary>\n\n{ch.to_markdown(index=False)}\n\n</details>\n"]
        md.append(f"```python\n{r['code']}\n```\n")
        rows.append(row)
    unload(cfg["default_model"])

new = pd.DataFrame(rows)
keep = old[~old.set_index(["provider", "method"]).index.isin(new.set_index(["provider", "method"]).index)]
pd.concat([keep, new]).sort_values(["method", "provider"]).to_csv(metrics_path, index=False)
if syn_rows:
    syn_path = OUT / "synthetic.csv"
    s_old = pd.read_csv(syn_path) if syn_path.exists() else pd.DataFrame(columns=["provider", "method"])
    s_new = pd.concat(syn_rows)
    s_old = s_old[~s_old.set_index(["provider", "method"]).index.isin(s_new.set_index(["provider", "method"]).index)]
    pd.concat([s_old, s_new]).to_csv(syn_path, index=False)
suffix = f"_{args.only or 'all'}_{args.method or 'all'}" if args.only or args.method else ""
(OUT / f"results{suffix}.md").write_text("\n".join(md), encoding="utf-8")
print(new[["provider", "method", "ok", "retries", "llm_seconds"]
          + [c for c in ["real_f1", "syn_f1", "syn_mae_min"] if c in new]].to_string(index=False))
