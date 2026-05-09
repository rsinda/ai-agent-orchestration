import json

import streamlit as st

from frontend.ui.api_client import ApiClient
from frontend.ui.components import (
    agent_label,
    api_guard,
    configure_page,
    dataframe,
    json_editor,
)


configure_page("Agents")
api = ApiClient()
st.title("Agents")
st.caption(
    "Create and configure agent behavior, models, tools, memory, limits, skills, rules, and guardrails."
)

agents = api_guard(api.list_agents, [])
tool_specs = api_guard(api.list_tools, [])
tool_names = ["memory", *[tool["name"] for tool in tool_specs]]

with st.expander("Create Agent", expanded=not agents):
    with st.form("create-agent"):
        name = st.text_input("Name", "Research Agent")
        role = st.text_input("Role", "researcher")
        system_prompt = st.text_area(
            "System prompt",
            "Research concise facts and pass them to the next agent.",
            height=140,
        )
        model = st.text_input(
            "Model override",
            "",
            help="Leave blank to use DEFAULT_MODEL, normally Gemini.",
        )
        tools = st.multiselect(
            "Tools",
            tool_names,
            default=["memory"],
            help="Choose from the backend tool registry.",
        )
        channels = st.text_input("Channels", "", help="Comma-separated, e.g. telegram.")
        limits, limits_error = json_editor(
            "Limits JSON", {"max_iterations": 2}, "create-limits", 110
        )
        memory, memory_error = json_editor(
            "Memory settings JSON",
            {"enabled": True, "scope": "workflow"},
            "create-memory",
            110,
        )
        guardrails, guardrails_error = json_editor(
            "Guardrails JSON", {"no_secrets": True}, "create-guardrails", 110
        )
        submitted = st.form_submit_button("Create Agent", type="primary")
        if submitted:
            if limits_error or memory_error or guardrails_error:
                st.error("Fix invalid JSON before creating the agent.")
            else:
                payload = {
                    "name": name,
                    "role": role,
                    "system_prompt": system_prompt,
                    "model": model,
                    "tools": tools,
                    "channels": [
                        item.strip() for item in channels.split(",") if item.strip()
                    ],
                    "limits": limits,
                    "memory_settings": memory,
                    "guardrails": guardrails,
                }
                agent = api_guard(lambda: api.create_agent(payload))
                if agent:
                    st.success(f"Created {agent['name']}")
                    st.rerun()

st.subheader("Existing Agents")
dataframe(agents, ["id", "name", "role", "model", "tools", "channels", "created_at"])

if agents:
    selected = st.selectbox("Edit agent", agents, format_func=agent_label)
    with st.form(f"edit-agent-{selected['id']}"):
        name = st.text_input("Name", selected.get("name", ""))
        role = st.text_input("Role", selected.get("role", ""))
        system_prompt = st.text_area(
            "System prompt", selected.get("system_prompt", ""), height=160
        )
        model = st.text_input("Model override", selected.get("model", ""))
        existing_tools = selected.get("tools") or []
        unknown_tools = [tool for tool in existing_tools if tool not in tool_names]
        selectable_tools = [*tool_names, *unknown_tools]
        tools = st.multiselect(
            "Tools",
            selectable_tools,
            default=existing_tools,
            help="Choose from the backend tool registry. Unknown saved tools are preserved here.",
        )
        channels = st.text_input("Channels", ", ".join(selected.get("channels") or []))
        limits, limits_error = json_editor(
            "Limits JSON", selected.get("limits") or {}, f"limits-{selected['id']}"
        )
        memory, memory_error = json_editor(
            "Memory settings JSON",
            selected.get("memory_settings") or {},
            f"memory-{selected['id']}",
        )
        guardrails, guardrails_error = json_editor(
            "Guardrails JSON",
            selected.get("guardrails") or {},
            f"guardrails-{selected['id']}",
        )
        interaction_rules, rules_error = json_editor(
            "Interaction rules JSON",
            (selected.get("guardrails") or {}).get("interaction_rules", {}),
            f"rules-{selected['id']}",
            120,
        )
        skills, skills_error = json_editor(
            "Skills JSON",
            (selected.get("memory_settings") or {}).get("skills", []),
            f"skills-{selected['id']}",
            120,
        )
        col1, col2 = st.columns([1, 1])
        save = col1.form_submit_button("Save Changes", type="primary")
        delete = col2.form_submit_button("Delete Agent")

        if save:
            if any(
                [
                    limits_error,
                    memory_error,
                    guardrails_error,
                    rules_error,
                    skills_error,
                ]
            ):
                st.error("Fix invalid JSON before saving.")
            else:
                guardrails = {
                    **(guardrails or {}),
                    "interaction_rules": interaction_rules,
                }
                memory = {**(memory or {}), "skills": skills}
                payload = {
                    "name": name,
                    "role": role,
                    "system_prompt": system_prompt,
                    "model": model,
                    "tools": tools,
                    "channels": [
                        item.strip() for item in channels.split(",") if item.strip()
                    ],
                    "limits": limits,
                    "memory_settings": memory,
                    "guardrails": guardrails,
                }
                updated = api_guard(lambda: api.update_agent(selected["id"], payload))
                if updated:
                    st.success("Agent updated.")
                    st.rerun()
        if delete:
            api_guard(lambda: api.delete_agent(selected["id"]))
            st.success("Agent deleted.")
            st.rerun()
