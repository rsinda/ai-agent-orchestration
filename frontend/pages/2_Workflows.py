import json

import pandas as pd
import streamlit as st

from frontend.ui.api_client import ApiClient
from frontend.ui.components import (
    agent_label,
    api_guard,
    configure_page,
    dataframe,
    workflow_label,
)
from frontend.ui.graph import render_workflow_graph
from frontend.ui.workflow_builder import (
    ROUTING_CONDITIONS,
    build_agent_nodes,
    build_agent_workflow,
    build_linear_agent_workflow,
    build_sequential_edges,
    normalize_edges,
)


configure_page("Workflows")
api = ApiClient()
st.title("Workflow Builder")
st.caption(
    "Create workflows from agents, instantiate templates, inspect graph definitions, and execute runs."
)

agents = api_guard(api.list_agents, [])
agents_by_id = {agent["id"]: agent for agent in agents}
workflows = api_guard(api.list_workflows, [])
templates = api_guard(api.list_templates, [])

template_tab, create_tab, builder_tab, run_tab = st.tabs(
    ["Templates", "Create", "Builder", "Run"]
)

with create_tab:
    st.subheader("Create Workflow From Agents")
    if not agents:
        st.info("Create at least one agent before building a workflow.")
    else:
        workflow_name = st.text_input("Workflow name", "New Agent Workflow")
        workflow_description = st.text_area(
            "Description",
            "A simple sequential workflow created from selected agents.",
            height=90,
        )
        agent_options = {agent_label(agent): agent for agent in agents}
        selected_agent_labels = st.multiselect(
            "Agents in execution order",
            list(agent_options.keys()),
            help="The first selected agent runs first, then each following agent receives the previous context.",
        )
        selected_agents = [agent_options[label] for label in selected_agent_labels]
        nodes = build_agent_nodes(selected_agents)
        edge_mode = st.radio("Routing", ["Sequential", "Custom"], horizontal=True)
        edited_edges = None
        if nodes and edge_mode == "Custom":
            node_ids = [node["id"] for node in nodes]
            edge_rows = [
                {**edge, "custom_condition": ""}
                for edge in build_sequential_edges(nodes)
            ]
            edited_edges = st.data_editor(
                pd.DataFrame(edge_rows),
                key="create-edge-editor",
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic",
                column_config={
                    "source": st.column_config.SelectboxColumn(
                        "source", options=node_ids, required=True
                    ),
                    "target": st.column_config.SelectboxColumn(
                        "target", options=[*node_ids, "END"], required=True
                    ),
                    "condition": st.column_config.SelectboxColumn(
                        "condition",
                        options=ROUTING_CONDITIONS,
                        required=True,
                    ),
                    "custom_condition": st.column_config.TextColumn("custom_condition"),
                    "label": st.column_config.TextColumn("label"),
                },
            )
            with st.expander("Edge JSON Preview"):
                preview_rows = edited_edges.to_dict("records")
                preview_edges, preview_errors = normalize_edges(preview_rows, node_ids)
                st.json(preview_edges)
                for error in preview_errors:
                    st.warning(error)
        submitted = st.button("Create Workflow", type="primary")

        if submitted:
            if not workflow_name.strip():
                st.error("Workflow name is required.")
            elif not selected_agents:
                st.error("Select at least one agent.")
            else:
                nodes = build_agent_nodes(selected_agents)
                if edge_mode == "Sequential":
                    payload = build_linear_agent_workflow(
                        workflow_name.strip(),
                        workflow_description.strip(),
                        selected_agents,
                    )
                    errors = []
                else:
                    edge_rows = (
                        edited_edges.to_dict("records")
                        if edited_edges is not None
                        else []
                    )
                    edges, errors = normalize_edges(
                        edge_rows, [node["id"] for node in nodes]
                    )
                    payload = build_agent_workflow(
                        workflow_name.strip(),
                        workflow_description.strip(),
                        nodes,
                        edges,
                    )
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    workflow = api_guard(lambda: api.create_workflow(payload))
                    if workflow:
                        st.session_state["selected_workflow_id"] = workflow["id"]
                        st.success(f"Created {workflow['name']}")
                        st.rerun()

with template_tab:
    st.subheader("Pre-built Templates")
    for template in templates:
        with st.container(border=True):
            st.markdown(f"**{template['name']}**")
            st.write(template["description"])
            name = st.text_input(
                "Workflow name",
                value=f"{template['name']} Demo",
                key=f"template-name-{template['id']}",
            )
            if st.button(
                "Instantiate", key=f"instantiate-{template['id']}", type="primary"
            ):
                workflow = api_guard(
                    lambda t=template, n=name: api.instantiate_template(t["id"], n)
                )
                if workflow:
                    st.session_state["selected_workflow_id"] = workflow["id"]
                    st.success(f"Created {workflow['name']}")
                    st.rerun()

with builder_tab:
    st.subheader("Visual Workflow Builder")
    if not workflows:
        st.info("Create or instantiate a workflow to begin.")
    else:
        selected = st.selectbox("Workflow", workflows, format_func=workflow_label)
        render_workflow_graph(selected, agents_by_id)

        definition = selected.get("definition") or {}
        nodes = definition.get("nodes") or []
        edges = definition.get("edges") or []
        st.markdown("**Nodes**")
        dataframe(nodes)
        st.markdown("**Edges and Conditions**")
        dataframe(edges)

        with st.expander("Advanced JSON Editor"):
            raw = st.text_area(
                "Workflow definition", json.dumps(definition, indent=2), height=360
            )
            if st.button("Save Workflow Definition"):
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError as exc:
                    st.error(f"Invalid JSON: {exc}")
                else:
                    updated = api_guard(
                        lambda: api.update_workflow(
                            selected["id"],
                            {
                                "name": selected["name"],
                                "description": selected.get("description", ""),
                                "definition": parsed,
                            },
                        )
                    )
                    if updated:
                        st.success("Workflow updated.")
                        st.rerun()

with run_tab:
    st.subheader("Execute Workflow")
    if workflows:
        selected = st.selectbox(
            "Workflow to run", workflows, format_func=workflow_label, key="run-workflow"
        )
        task = st.text_area(
            "Task input", "Compare pgvector and Qdrant for agent memory.", height=120
        )
        user_id = st.text_input("User id", "streamlit-user")
        async_run = st.checkbox("Run asynchronously", value=False)
        if st.button("Run Workflow", type="primary"):
            run = api_guard(
                lambda: api.run_workflow(selected["id"], task, user_id, async_run)
            )
            if run:
                st.session_state["selected_run_id"] = run["id"]
                st.success(f"Run {run['status']}: {run['id']}")
                st.code(run.get("output") or "Run started. Open Runs to monitor.")
    else:
        st.info("No workflows available.")
