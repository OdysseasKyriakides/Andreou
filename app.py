"""
BPM-GenAI digital assistant (Steps 3, 4, 5).

Run locally:   python -m streamlit run app.py
LLMs:          two local Ollama models, Gemma (bpm-gemma4) and Qwen (bpm-qwen); see llm.py
"""
import json

import pandas as pd
import streamlit as st

from assistant import EXAMPLES_STEP3, ask_log, summarize_trace
from llm import PROVIDERS, unload
from log_data import build_cases, load_events
from step5_fix import METHODS, changes_table, corrected_log, evaluate_fix, generate_fix

st.set_page_config(page_title="Claims Process Assistant", page_icon="📊", layout="wide")


@st.cache_data
def get_data():
    events = load_events()
    return events, build_cases(events)


events, cases = get_data()

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("LLM settings")
    mode = st.radio("Run with", ["Both (side by side)"] + list(PROVIDERS))
    llms = {name: st.text_input(f"{name} model (Ollama)", cfg["default_model"])
            for name, cfg in PROVIDERS.items()}
    st.caption("Both LLMs run locally with Ollama: no API keys, no quotas.")
    st.divider()
    st.caption(f"Log: {len(events)} events, {len(cases)} cases")

selected = list(PROVIDERS) if mode.startswith("Both") else [mode]


def columns_for(providers):
    return st.columns(len(providers)) if len(providers) > 1 else [st.container()]


def usage_caption(provider, r, extra=""):
    st.caption(f"{provider} · {llms[provider]} · {r['seconds']:.1f} s · "
               f"{r['input_tokens']} in / {r['output_tokens']} out tokens{extra}")


st.title("Insurance Claims - Process Assistant")
tab3, tab4, tab5 = st.tabs(["Step 3 - Ask the log", "Step 4 - Trace summary", "Step 5 - Fix timestamps"])

# ---------------------------------------------------------------- Step 3
with tab3:
    st.write("Ask a question in English. The LLM writes pandas code, the app runs it on the real log "
             "and shows the computed table and chart.")
    example = st.selectbox("Examples", [""] + EXAMPLES_STEP3)
    question = st.text_area("Question", value=example, height=80)

    if st.button("Ask", type="primary", disabled=not question.strip()):
        for provider, col in zip(selected, columns_for(selected)):
            with col:
                st.subheader(provider)
                with st.spinner(f"{provider} is writing code..."):
                    try:
                        r = ask_log(provider, llms[provider], question, events, cases)
                    except Exception as e:
                        st.error(f"LLM call failed: {e}")
                        continue
                if r["error"]:
                    st.error(f"The generated code failed twice: {r['error']}")
                else:
                    if r["answer"]:
                        st.success(r["answer"])
                    if isinstance(r["result"], pd.DataFrame):
                        st.dataframe(r["result"], width="stretch")
                    elif r["result"] is not None:
                        st.write(r["result"])
                    if r["fig"] is not None:
                        st.plotly_chart(r["fig"], width="stretch", key=f"fig_{provider}")
                usage_caption(provider, r, " · fixed after 1 retry" if r["retries"] else "")
                with st.expander("Generated code"):
                    st.code(r["code"], language="python")

    with st.expander("Data preview"):
        st.dataframe(events, width="stretch", height=250)

# ---------------------------------------------------------------- Step 4
with tab4:
    st.write("Pick a claim. The facts (times, waits, costs, bottleneck, data-quality issues) are computed "
             "by code; the LLM only turns them into a narrative. Every number it writes is then checked "
             "against the facts.")
    case = st.selectbox("Case ID", cases["case"].tolist())
    st.dataframe(events[events["case"] == case].drop(columns=["case_num"]), width="stretch", hide_index=True)

    if st.button("Summarize trace", type="primary"):
        facts = None
        for provider, col in zip(selected, columns_for(selected)):
            with col:
                st.subheader(provider)
                with st.spinner(f"{provider} is writing the summary..."):
                    try:
                        r = summarize_trace(provider, llms[provider], case, events, cases)
                    except Exception as e:
                        st.error(f"LLM call failed: {e}")
                        continue
                facts = r["facts"]
                st.info(r["text"])
                chk = r["check"]
                if chk["unverified"]:
                    st.warning(f"Numbers checked: {chk['verified']}/{chk['numbers']} found in the facts. "
                               f"Not found (possible hallucination): {chk['unverified']}")
                else:
                    st.caption(f"Numbers checked: {chk['verified']}/{chk['numbers']} found in the facts.")
                usage_caption(provider, r)
        if facts:
            with st.expander("Facts sent to the LLM (computed by code)"):
                st.code(json.dumps(facts, indent=1), language="json")

with tab5:
    st.write("Each LLM writes Python code that **detects and corrects** the wrong timestamps, with a "
             "statistical method (median waiting times) or a machine-learning method (regression on the "
             "waiting time). The app runs the code on the real log and scores it: detection against the Step 1 "
             "ground truth (22 claims), and correction accuracy on copies of the log with synthetic errors "
             "whose true timestamps are known.")
    methods = st.multiselect("Method", METHODS, default=METHODS)

    if st.button("Generate and run the correction", type="primary", disabled=not methods):
        for method in methods:
            st.subheader(f"Method: {method}")
            for provider, col in zip(selected, columns_for(selected)):
                with col:
                    st.markdown(f"**{provider}**")
                    with st.spinner(f"{provider} is writing the {method.lower()} correction..."):
                        try:
                            r = generate_fix(provider, llms[provider], method, events)
                        except Exception as e:
                            st.error(f"LLM call failed: {e}")
                            continue
                    if r["error"]:
                        st.error(f"The generated code failed {r['retries'] + 1} times. Last error: {r['error']}")
                    else:
                        with st.spinner("Scoring on the real log and 5 synthetic logs..."):
                            m, _ = evaluate_fix(r["code"], events, r["fixed"], r["answer"])
                        st.success(r["answer"] or "(no summary)")
                        a, b, c, d = st.columns(4)
                        a.metric("Precision (real)", f"{m['real_precision']:.2f}")
                        b.metric("Recall (real)", f"{m['real_recall']:.2f}")
                        c.metric("F1 (real)", f"{m['real_f1']:.2f}")
                        d.metric("Claims in order", f"{m['real_cases_in_order']:.0%}")
                        a, b, c, d = st.columns(4)
                        a.metric("F1 (synthetic)", f"{m['syn_f1']:.2f}")
                        b.metric("MAE (synthetic)", f"{m['syn_mae_min']:.0f} min")
                        c.metric("Within 60 min", f"{m['syn_within_60min']:.0%}")
                        d.metric("Order restored", f"{m['syn_order_restored']:.0%}")
                        problems = []
                        if m["nat_left"]:
                            problems.append(f"{m['nat_left']} timestamps left empty")
                        if m["silent_changes"]:
                            problems.append(f"{m['silent_changes']} timestamps changed without being flagged")
                        if m["answer_unverified"]:
                            problems.append(f"{m['answer_unverified']} numbers in the summary do not match its own output")
                        if problems:
                            st.warning("Contract problems (possible hallucination): " + "; ".join(problems))
                        st.dataframe(changes_table(r["fixed"], events), hide_index=True, width="stretch", height=220)
                        st.download_button("Download corrected log (CSV)",
                                           corrected_log(r["fixed"], events).to_csv(index=False),
                                           file_name=f"{provider}_{method}_corrected.csv",
                                           key=f"dl_{provider}_{method}")
                    usage_caption(provider, r, f" · {r['retries']} retries" if r["retries"] else "")
                    with st.expander("Generated code"):
                        st.code(r["code"], language="python")
                if len(selected) > 1:
                    unload(llms[provider])  # two models do not fit in the GPU memory together
