import streamlit as st

from frontend.ui.api_client import ApiClient
from frontend.ui.components import api_guard, configure_page, dataframe, status_badge, workflow_label


configure_page("Agent Orchestration Dashboard")
api = ApiClient()

st.title("AI Agent Orchestration Platform")
st.caption("Visual console for agents, workflows, runtime monitoring, memory, and Telegram integration.")

health = api_guard(api.health, {})
agents = api_guard(api.list_agents, [])
workflows = api_guard(api.list_workflows, [])
runs = api_guard(lambda: api.list_runs(10), [])
telegram = api_guard(api.telegram_status, {})

metric_cols = st.columns(5)
metric_cols[0].metric("Backend", health.get("status", "down"))
metric_cols[1].metric("Agents", len(agents))
metric_cols[2].metric("Workflows", len(workflows))
metric_cols[3].metric("Recent runs", len(runs))
metric_cols[4].metric("Telegram", "Ready" if telegram.get("polling_enabled") else "Needs setup")

st.divider()

left, right = st.columns([1, 1])

with left:
    st.subheader("Quick Template Launch")
    templates = api_guard(api.list_templates, [])
    template_options = {template["name"]: template["id"] for template in templates}
    if template_options:
        template_name = st.selectbox("Template", list(template_options.keys()))
        workflow_name = st.text_input("Workflow name", value=f"{template_name} Demo")
        if st.button("Instantiate Template", type="primary"):
            workflow = api_guard(lambda: api.instantiate_template(template_options[template_name], workflow_name))
            if workflow:
                st.session_state["selected_workflow_id"] = workflow["id"]
                st.success(f"Created workflow: {workflow['name']}")

    st.subheader("Run Workflow")
    workflow_options = {workflow_label(workflow): workflow["id"] for workflow in workflows}
    if workflow_options:
        default_index = 0
        selected_id = st.session_state.get("selected_workflow_id")
        option_keys = list(workflow_options.keys())
        if selected_id:
            for index, label in enumerate(option_keys):
                if workflow_options[label] == selected_id:
                    default_index = index
                    break
        selected_workflow = st.selectbox("Workflow", option_keys, index=default_index)
        run_input = st.text_area("Task", "Compare pgvector and Qdrant for agent memory.")
        user_id = st.text_input("User id", "demo-user")
        if st.button("Run Now"):
            run = api_guard(lambda: api.run_workflow(workflow_options[selected_workflow], run_input, user_id, False))
            if run:
                st.session_state["selected_run_id"] = run["id"]
                st.success(f"Run finished: {run['status']}")
                st.code(run.get("output", ""))
    else:
        st.info("Create or instantiate a workflow first.")

with right:
    st.subheader("Latest Runs")
    for run in runs[:5]:
        with st.container(border=True):
            cols = st.columns([2, 1])
            cols[0].markdown(f"**{run['id'][:8]}**")
            with cols[1]:
                status_badge(run.get("status", "unknown"))
            st.caption(run.get("input", "")[:180])
            if st.button("Inspect", key=f"inspect-{run['id']}"):
                st.session_state["selected_run_id"] = run["id"]
                st.switch_page("pages/4_Runs.py")

st.subheader("Recent Run Table")
dataframe(runs, ["id", "workflow_id", "status", "input", "output", "cost_usd", "created_at"])

