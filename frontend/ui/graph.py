import html
from typing import Any

import streamlit as st


def render_workflow_graph(workflow: dict[str, Any], agents_by_id: dict[str, dict[str, Any]] | None = None) -> None:
    definition = workflow.get("definition") or {}
    nodes = definition.get("nodes") or []
    edges = definition.get("edges") or []
    if not nodes:
        st.info("This workflow has no nodes yet.")
        return

    lines = [
        "digraph workflow {",
        "rankdir=LR;",
        'node [shape=box, style="rounded,filled", fillcolor="#f8fafc", color="#64748b", fontname="Helvetica"];',
        'edge [fontname="Helvetica", color="#475569"];',
    ]

    for node in nodes:
        node_id = node.get("id", "")
        agent = (agents_by_id or {}).get(node.get("agent_id", ""), {})
        label = f"{node_id}\\n{agent.get('name', node.get('type', 'node'))}"
        lines.append(f'"{_esc(node_id)}" [label="{_esc(label)}"];')

    lines.append('"END" [shape=oval, fillcolor="#ecfeff"];')
    for edge in edges:
        source = edge.get("source", "")
        target = edge.get("target", "END")
        condition = edge.get("condition", "always")
        color = "#dc2626" if "revision" in str(condition) else "#475569"
        lines.append(f'"{_esc(source)}" -> "{_esc(target)}" [label="{_esc(str(condition))}", color="{color}"];')

    lines.append("}")
    st.graphviz_chart("\n".join(lines), use_container_width=True)


def _esc(value: str) -> str:
    return html.escape(str(value), quote=True).replace("\n", "\\n")

