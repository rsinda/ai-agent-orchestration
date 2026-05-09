import re
from typing import Any


ROUTING_CONDITIONS = [
    "always",
    "else",
    "critic_needs_revision",
    "critic_approved",
    "custom",
]


def build_linear_agent_workflow(
    name: str,
    description: str,
    agents: list[dict[str, Any]],
) -> dict[str, Any]:
    nodes = build_agent_nodes(agents)
    return build_agent_workflow(name, description, nodes, build_sequential_edges(nodes))


def build_agent_nodes(agents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nodes = []
    for index, agent in enumerate(agents, start=1):
        node_id = _node_id(agent, index)
        nodes.append(
            {
                "id": node_id,
                "type": "agent",
                "label": agent.get("name") or f"Agent {index}",
                "agent_id": agent["id"],
                "recipient_id": "workflow",
            }
        )
    return nodes


def build_sequential_edges(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edges = []
    for index, node in enumerate(nodes):
        if index > 0:
            edges.append(
                {
                    "source": nodes[index - 1]["id"],
                    "target": node["id"],
                    "condition": "always",
                    "label": "then",
                }
            )
    if nodes:
        edges.append(
            {
                "source": nodes[-1]["id"],
                "target": "END",
                "condition": "always",
                "label": "finish",
            }
        )
    return edges


def build_agent_workflow(
    name: str,
    description: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "definition": {
            "start_node": nodes[0]["id"] if nodes else None,
            "nodes": nodes,
            "edges": edges,
        },
    }


def normalize_edges(
    rows: list[dict[str, Any]],
    node_ids: list[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    edges = []
    errors = []
    valid_targets = {*node_ids, "END"}
    for index, row in enumerate(rows, start=1):
        source = str(row.get("source") or "").strip()
        target = str(row.get("target") or "").strip()
        condition = str(row.get("condition") or "always").strip()
        custom_condition = str(row.get("custom_condition") or "").strip()
        label = str(row.get("label") or "").strip()

        if not source and not target:
            continue
        if source not in node_ids:
            errors.append(f"Edge {index}: source must be one of the selected nodes.")
        if target not in valid_targets:
            errors.append(f"Edge {index}: target must be a selected node or END.")
        if condition == "custom":
            condition = custom_condition
            if not condition:
                errors.append(f"Edge {index}: custom condition is required.")
        elif condition not in ROUTING_CONDITIONS:
            errors.append(f"Edge {index}: condition is not supported.")

        if source in node_ids and target in valid_targets and condition:
            edge = {
                "source": source,
                "target": target,
                "condition": condition,
            }
            if label:
                edge["label"] = label
            edges.append(edge)

    return edges, errors


def _node_id(agent: dict[str, Any], index: int) -> str:
    base = agent.get("name") or agent.get("role") or f"agent-{index}"
    slug = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
    return f"{index}-{slug or 'agent'}"
