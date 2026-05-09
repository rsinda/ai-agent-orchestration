import time

import streamlit as st

from frontend.ui.api_client import ApiClient
from frontend.ui.components import api_guard, configure_page, dataframe, status_badge


configure_page("Runs")
api = ApiClient()
st.title("Runs & Live Monitoring")
st.caption("Inspect run status, agent messages, event timeline, token usage, and cost.")

runs = api_guard(lambda: api.list_runs(50), [])
if not runs:
    st.info("No runs yet.")
    st.stop()

run_ids = [run["id"] for run in runs]
default_id = st.session_state.get("selected_run_id")
default_index = run_ids.index(default_id) if default_id in run_ids else 0
selected_id = st.selectbox("Run", run_ids, index=default_index, format_func=lambda rid: f"{rid[:8]} · {next((r['status'] for r in runs if r['id'] == rid), '')}")
st.session_state["selected_run_id"] = selected_id

auto_refresh = st.checkbox("Auto-refresh running run", value=False)

run = api_guard(lambda: api.get_run(selected_id), {})
messages = api_guard(lambda: api.get_run_messages(selected_id), [])
events = api_guard(lambda: api.get_run_events(selected_id), [])

cols = st.columns(5)
cols[0].metric("Status", run.get("status", "unknown"))
cols[1].metric("Prompt tokens", (run.get("token_usage") or {}).get("prompt_tokens", 0))
cols[2].metric("Completion tokens", (run.get("token_usage") or {}).get("completion_tokens", 0))
cols[3].metric("Cost", f"${run.get('cost_usd', 0):.4f}")
cols[4].metric("Messages", len(messages))

st.subheader("Input")
st.write(run.get("input") or "")
st.subheader("Output")
st.code(run.get("output") or "")

message_tab, event_tab, raw_tab = st.tabs(["Messages", "Events", "Raw Run"])

with message_tab:
    for message in messages:
        with st.container(border=True):
            st.markdown(f"**{message['channel']}** · `{message['sender_id']}` -> `{message['recipient_id']}`")
            st.write(message["content"])
            st.caption(message["created_at"])

with event_tab:
    dataframe(events, ["event_type", "node_id", "payload", "created_at"])

with raw_tab:
    st.json(run)

if auto_refresh and run.get("status") in {"pending", "running"}:
    time.sleep(3)
    st.rerun()

