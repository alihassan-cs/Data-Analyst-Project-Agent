import os
import shutil
import tempfile

import streamlit as st

from agent import PROVIDERS, DataAgent, find_csvs, load_notes
from charts import show_chart, stretch

st.set_page_config(page_title="Data Analyst Agent", page_icon="📊", layout="wide")
st.title("📊 Data Analyst Agent")
st.caption("Ask questions about your CSV data in plain English. "
           "The agent writes and runs read-only SQL, then answers from the results.")

# ---------- sidebar ----------
with st.sidebar:
    st.header("Settings")
    provider = st.selectbox("Model provider", list(PROVIDERS), index=0)
    env_name = PROVIDERS[provider]["key_env"]
    typed_key = st.text_input(f"{env_name}", type="password",
                              help="Paste your own key. If empty, the key from the server's environment is used.")
    api_key = typed_key or os.getenv(env_name, "")
    st.caption(f"Model: `{PROVIDERS[provider]['model']}`")
    st.markdown(
        "**Privacy:** your data is sent to the selected provider's API to answer questions. "
        "Do not upload sensitive personal data. Free-tier keys may allow the provider to use your data."
    )
    sample_paths = find_csvs("data")
    use_sample = False
    if sample_paths:
        use_sample = st.checkbox(f"Use sample data in /data ({len(sample_paths)} files)", value=True)

files = st.file_uploader("Or upload one or more CSV files", type="csv", accept_multiple_files=True)

if files:
    source_sig = tuple((f.name, f.size) for f in files)
elif use_sample:
    source_sig = tuple(sample_paths)
else:
    st.info("Upload a CSV, or put CSV files in the `data/` folder.")
    st.stop()

if not api_key:
    st.info(f"Enter your {env_name} in the sidebar to start.")
    st.stop()

sig = (provider, hash(api_key), source_sig)
if st.session_state.get("sig") != sig:
    with st.spinner("Loading data..."):
        try:
            if files:
                tmp = tempfile.mkdtemp()
                paths = []
                for f in files:
                    p = os.path.join(tmp, os.path.basename(f.name))
                    with open(p, "wb") as out:
                        out.write(f.getbuffer())
                    paths.append(p)
                try:
                    agent = DataAgent(paths, provider=provider, api_key=api_key, log_path="logs.jsonl")
                finally:
                    shutil.rmtree(tmp, ignore_errors=True)  # delete uploaded files from disk
            else:
                agent = DataAgent(sample_paths, provider=provider, api_key=api_key,
                                  notes=load_notes(), log_path="logs.jsonl")
        except Exception as e:  # noqa: BLE001
            st.error(f"Could not start: {e}")
            st.stop()
    st.session_state.agent = agent
    st.session_state.sig = sig
    st.session_state.chat = []

agent = st.session_state.agent

with st.expander("Detected schema"):
    st.text(agent.schema)


def show_extras(m, key):
    df = m.get("df")
    if df is not None:
        stretch(st.dataframe, df.head(100))
        st.download_button("Download result as CSV", df.to_csv(index=False),
                           file_name="result.csv", mime="text/csv", key=f"dl_{key}")
        show_chart(df, key, m.get("question", ""))
    if m.get("queries"):
        with st.expander("SQL used"):
            for q in m["queries"]:
                st.code(q, language="sql")
    if m.get("stats"):
        s = m["stats"]
        st.caption(f"{s['tokens_in']} tokens in / {s['tokens_out']} out · {s['seconds']}s · {s['queries']} queries")


for i, m in enumerate(st.session_state.chat):
    with st.chat_message(m["role"]):
        st.write(m["content"])
        if m["role"] == "assistant":
            show_extras(m, i)

if q := st.chat_input("Ask a question about your data"):
    history = [{"role": m["role"], "content": m["content"][:600]} for m in st.session_state.chat[-2:]]
    st.session_state.chat.append({"role": "user", "content": q})
    with st.chat_message("user"):
        st.write(q)
    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            try:
                ans = agent.ask(q, history)
            except Exception as e:  # noqa: BLE001
                ans = f"Error: {e}"
        st.write(ans)
        entry = {"role": "assistant", "content": ans, "question": q, "df": agent.last_df,
                 "queries": list(agent.queries), "stats": agent.last_stats}
        show_extras(entry, len(st.session_state.chat))
        st.caption("AI can be wrong. Verify important numbers before acting on them.")
    st.session_state.chat.append(entry)

if st.sidebar.button("Clear chat"):
    st.session_state.chat = []
    st.rerun()
