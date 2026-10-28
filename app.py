"""
BPM-GenAI digital assistant (Steps 3, 4, 5).

Run locally:   python -m streamlit run app.py
API keys:      .streamlit/secrets.toml (see secrets.toml.example) or paste them in the sidebar
"""
import json
import os

import pandas as pd
import streamlit as st

from assistant import EXAMPLES_STEP3, ask_log, summarize_trace
from llm import PROVIDERS
from log_data import build_cases, load_events

st.set_page_config(page_title="Claims Process Assistant", page_icon="📊", layout="wide")


@st.cache_data
def get_data():
    events = load_events()
    return events, build_cases(events)


def get_key(name):
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.environ.get(name, "")


events, cases = get_data()

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("LLM settings")
    mode = st.radio("Run with", ["Both (side by side)"] + list(PROVIDERS))
    llms = {}
    for name, cfg in PROVIDERS.items():
        model = st.text_input(f"{name} model", cfg["default_model"])
        key = get_key(cfg["key_name"]) or st.text_input(cfg["key_name"], type="password")
        llms[name] = (model, key)
    st.caption("Keys are read from secrets, or kept only for this session if pasted.")
    st.divider()
    st.caption(f"Log: {len(events)} events, {len(cases)} cases")

selected = list(PROVIDERS) if mode.startswith("Both") else [mode]
missing = [p for p in selected if not llms[p][1]]


def columns_for(providers):
    return st.columns(len(providers)) if len(providers) > 1 else [st.container()]


def usage_caption(provider, r, extra=""):
    st.caption(f"{provider} · {llms[provider][0]} · {r['seconds']:.1f} s · "
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
        if missing:
            st.error(f"Add an API key for {', '.join(missing)} in the sidebar.")
            st.stop()
        for provider, col in zip(selected, columns_for(selected)):
            with col:
                st.subheader(provider)
                with st.spinner(f"{provider} is writing code..."):
                    try:
                        r = ask_log(provider, *llms[provider], question, events, cases)
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
        if missing:
            st.error(f"Add an API key for {', '.join(missing)} in the sidebar.")
            st.stop()
        facts = None
        for provider, col in zip(selected, columns_for(selected)):
            with col:
                st.subheader(provider)
                with st.spinner(f"{provider} is writing the summary..."):
                    try:
                        r = summarize_trace(provider, *llms[provider], case, events, cases)
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
    st.info("Step 5 - coming next: fix the timestamp errors with a statistical and an ML method using both LLMs.")
