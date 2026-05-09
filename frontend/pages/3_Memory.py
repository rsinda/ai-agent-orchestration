import streamlit as st

from frontend.ui.api_client import ApiClient
from frontend.ui.components import agent_label, api_guard, configure_page, dataframe, workflow_label


configure_page("Memory")
api = ApiClient()
st.title("Memory")
st.caption("Add and recall scoped semantic memory records.")

agents = api_guard(api.list_agents, [])
workflows = api_guard(api.list_workflows, [])
runs = api_guard(lambda: api.list_runs(50), [])

agent_options = {"Any": None, **{agent_label(agent): agent["id"] for agent in agents}}
workflow_options = {"Any": None, **{workflow_label(workflow): workflow["id"] for workflow in workflows}}
run_options = {"Any": None, **{f"{run['id'][:8]} · {run['status']}": run["id"] for run in runs}}

add_tab, recall_tab = st.tabs(["Add Memory", "Recall"])

with add_tab:
    with st.form("add-memory"):
        content = st.text_area("Memory content", height=180)
        agent_id = agent_options[st.selectbox("Agent", list(agent_options.keys()))]
        workflow_id = workflow_options[st.selectbox("Workflow", list(workflow_options.keys()))]
        run_id = run_options[st.selectbox("Run", list(run_options.keys()))]
        user_id = st.text_input("User id")
        scope = st.selectbox("Memory scope", ["workflow", "agent", "user", "global"])
        memory_type = st.selectbox("Memory type", ["message", "fact", "preference", "summary"])
        if st.form_submit_button("Remember", type="primary"):
            payload = {
                "content": content,
                "agent_id": agent_id,
                "workflow_id": workflow_id,
                "run_id": run_id,
                "user_id": user_id or None,
                "memory_scope": scope,
                "memory_type": memory_type,
            }
            result = api_guard(lambda: api.remember(payload))
            if result:
                st.success(f"Stored memory {result['id']}")

with recall_tab:
    query = st.text_input("Recall query", "agent memory pgvector qdrant")
    col1, col2, col3 = st.columns(3)
    agent_id = agent_options[col1.selectbox("Filter agent", list(agent_options.keys()), key="recall-agent")]
    workflow_id = workflow_options[col2.selectbox("Filter workflow", list(workflow_options.keys()), key="recall-workflow")]
    run_id = run_options[col3.selectbox("Filter run", list(run_options.keys()), key="recall-run")]
    user_id = st.text_input("Filter user id")
    limit = st.slider("Limit", 1, 50, 5)

    if st.button("Recall Memory", type="primary"):
        filters = {
            key: value
            for key, value in {
                "agent_id": agent_id,
                "workflow_id": workflow_id,
                "run_id": run_id,
                "user_id": user_id or None,
            }.items()
            if value
        }
        hits = api_guard(lambda: api.recall_memory(query, filters, limit), [])
        for hit in hits:
            with st.container(border=True):
                st.markdown(f"**Score:** `{hit['score']:.4f}` · **Type:** `{hit['memory_type']}` · **Scope:** `{hit['memory_scope']}`")
                st.write(hit["content"])
                st.caption(f"{hit['id']} · {hit['created_at']}")

