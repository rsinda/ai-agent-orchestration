from frontend.ui.workflow_builder import (
    build_agent_nodes,
    build_agent_workflow,
    build_linear_agent_workflow,
    normalize_edges,
)


def test_build_linear_agent_workflow_creates_agent_nodes_and_edges():
    payload = build_linear_agent_workflow(
        "Demo workflow",
        "Runs two agents in order.",
        [
            {"id": "agent-1", "name": "Research Agent"},
            {"id": "agent-2", "name": "Writer Agent"},
        ],
    )

    definition = payload["definition"]
    assert payload["name"] == "Demo workflow"
    assert definition["start_node"] == "1-research-agent"
    assert definition["nodes"] == [
        {
            "id": "1-research-agent",
            "type": "agent",
            "label": "Research Agent",
            "agent_id": "agent-1",
            "recipient_id": "workflow",
        },
        {
            "id": "2-writer-agent",
            "type": "agent",
            "label": "Writer Agent",
            "agent_id": "agent-2",
            "recipient_id": "workflow",
        },
    ]
    assert definition["edges"] == [
        {
            "source": "1-research-agent",
            "target": "2-writer-agent",
            "condition": "always",
            "label": "then",
        },
        {
            "source": "2-writer-agent",
            "target": "END",
            "condition": "always",
            "label": "finish",
        },
    ]


def test_build_agent_workflow_accepts_custom_conditional_edges():
    nodes = build_agent_nodes(
        [
            {"id": "agent-1", "name": "Triage"},
            {"id": "agent-2", "name": "Specialist"},
        ]
    )
    edges, errors = normalize_edges(
        [
            {
                "source": "1-triage",
                "target": "2-specialist",
                "condition": "custom",
                "custom_condition": "needs_specialist",
                "label": "specialist",
            },
            {
                "source": "1-triage",
                "target": "END",
                "condition": "else",
                "label": "done",
            },
        ],
        [node["id"] for node in nodes],
    )

    payload = build_agent_workflow("Conditional", "", nodes, edges)

    assert errors == []
    assert payload["definition"]["edges"] == [
        {
            "source": "1-triage",
            "target": "2-specialist",
            "condition": "needs_specialist",
            "label": "specialist",
        },
        {
            "source": "1-triage",
            "target": "END",
            "condition": "else",
            "label": "done",
        },
    ]


def test_normalize_edges_reports_invalid_routes():
    edges, errors = normalize_edges(
        [
            {
                "source": "missing",
                "target": "END",
                "condition": "custom",
                "custom_condition": "",
            }
        ],
        ["agent"],
    )

    assert edges == []
    assert errors == [
        "Edge 1: source must be one of the selected nodes.",
        "Edge 1: custom condition is required.",
    ]
