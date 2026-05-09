import streamlit as st

from frontend.ui.api_client import ApiClient
from frontend.ui.components import api_guard, configure_page, dataframe, workflow_label


configure_page("Telegram")
api = ApiClient()
st.title("Telegram")
st.caption("Connect a Telegram bot to a default workflow and monitor channel-triggered runs.")

status = api_guard(api.telegram_status, {})
workflows = api_guard(api.list_workflows, [])
runs = api_guard(lambda: api.list_runs(25), [])

cols = st.columns(3)
cols[0].metric("Binding", "Connected" if status.get("connected") else "Missing")
cols[1].metric("Token", "Configured" if status.get("token_configured") else "Missing")
cols[2].metric("Polling", "Enabled" if status.get("polling_enabled") else "Inactive")

st.subheader("Setup Checklist")
st.checkbox("Create a bot with BotFather", value=status.get("token_configured", False), disabled=True)
st.checkbox("Set TELEGRAM_BOT_TOKEN in .env or enter one below", value=status.get("token_configured", False), disabled=True)
st.checkbox("Connect a default workflow", value=status.get("connected", False), disabled=True)
st.checkbox("Restart backend after changing .env", value=status.get("polling_enabled", False), disabled=True)

st.subheader("Connect Bot")
if workflows:
    workflow_options = {workflow_label(workflow): workflow["id"] for workflow in workflows}
    selected_workflow = st.selectbox("Default workflow", list(workflow_options.keys()))
    bot_name = st.text_input("Binding name", status.get("name") or "Telegram Bot")
    token = st.text_input("Bot token", "", type="password", help="Optional if TELEGRAM_BOT_TOKEN is set in backend env.")
    if st.button("Connect Telegram", type="primary"):
        binding = api_guard(lambda: api.connect_telegram(workflow_options[selected_workflow], bot_name, token or None))
        if binding:
            st.success("Telegram connected. Send your bot a message in the Telegram app.")
            st.rerun()
else:
    st.info("Create a workflow before connecting Telegram.")

st.subheader("Recent Runs")
dataframe(runs, ["id", "workflow_id", "status", "input", "output", "created_at"])

