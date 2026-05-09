import json

import streamlit as st

from frontend.ui.api_client import ApiClient
from frontend.ui.components import api_guard, configure_page, dataframe


configure_page("Tools")
api = ApiClient()
st.title("Tools")
st.caption("Inspect and execute registered runtime tools.")

tools = api_guard(api.list_tools, [])

if not tools:
    st.info("No tools are registered.")
    st.stop()

tool_options = {f"{tool['name']} - {tool['description']}": tool for tool in tools}
selected_label = st.selectbox("Tool registry", list(tool_options.keys()))
selected = tool_options[selected_label]

left, right = st.columns([1, 1])
with left:
    st.subheader("Schema")
    st.json(selected.get("input_schema") or {})

with right:
    st.subheader("Execute")
    default_arguments = {
        "calculator": {"expression": "(2 + 3) * 4"},
        "web_search": {"query": "latest open source vector databases", "max_results": 5},
        "current_time": {"timezone": "Asia/Kolkata"},
        "text_stats": {"text": "Agent workflows need observable tools."},
    }.get(selected["name"], {})
    raw_arguments = st.text_area("Arguments JSON", json.dumps(default_arguments, indent=2), height=180)
    if st.button("Run Tool", type="primary"):
        try:
            arguments = json.loads(raw_arguments or "{}")
        except json.JSONDecodeError as exc:
            st.error(f"Invalid JSON: {exc}")
        else:
            result = api_guard(lambda: api.execute_tool(selected["name"], arguments))
            if result:
                st.success("Tool executed.")
                st.markdown("**Result**")
                st.write(result["content"])
                st.markdown("**Raw data**")
                st.json(result.get("data") or {})

st.subheader("Registry")
dataframe(tools, ["name", "description", "input_schema"])
