def test_tool_api_lists_and_executes_calculator(client):
    listed = client.get("/tools")
    assert listed.status_code == 200
    names = {tool["name"] for tool in listed.json()}
    assert {"calculator", "web_search", "current_time", "text_stats"}.issubset(names)

    executed = client.post("/tools/calculator/execute", json={"arguments": {"expression": "(2 + 3) * 4"}})
    assert executed.status_code == 200
    body = executed.json()
    assert body["name"] == "calculator"
    assert body["data"]["result"] == 20
    assert "(2 + 3) * 4 = 20" in body["content"]


def test_workflow_tool_node_executes_and_persists_message(client):
    workflow = client.post(
        "/workflows",
        json={
            "name": "Calculator Tool Workflow",
            "description": "Verifies tool nodes execute inside the runtime.",
            "definition": {
                "start_node": "calculate",
                "nodes": [
                    {
                        "id": "calculate",
                        "type": "tool",
                        "tool_name": "calculator",
                        "input": {"expression": "12 / 3 + 5"},
                    }
                ],
                "edges": [{"source": "calculate", "target": "END", "condition": "always"}],
            },
        },
    )
    assert workflow.status_code == 201

    run = client.post(
        f"/workflows/{workflow.json()['id']}/runs",
        json={"input": "Calculate this.", "execute_async": False},
    )
    assert run.status_code == 201
    run_body = run.json()
    assert run_body["status"] == "succeeded"
    assert "12 / 3 + 5 = 9.0" in run_body["output"]

    messages = client.get(f"/runs/{run_body['id']}/messages")
    assert messages.status_code == 200
    assert messages.json()[0]["channel"] == "tool"
    assert messages.json()[0]["sender_id"] == "tool:calculator"

    events = client.get(f"/runs/{run_body['id']}/events")
    event_types = {event["event_type"] for event in events.json()}
    assert "tool_call_started" in event_types
    assert "tool_call_finished" in event_types


def test_agent_can_use_calculator_tool_context(client):
    agent = client.post(
        "/agents",
        json={
            "name": "Math Agent",
            "role": "math helper",
            "system_prompt": "Use tool results when they are available.",
            "model": "mock-agent",
            "tools": ["calculator"],
            "channels": [],
        },
    )
    assert agent.status_code == 201

    workflow = client.post(
        "/workflows",
        json={
            "name": "Agent Tool Context Workflow",
            "description": "",
            "definition": {
                "start_node": "math",
                "nodes": [{"id": "math", "type": "agent", "agent_id": agent.json()["id"]}],
                "edges": [{"source": "math", "target": "END", "condition": "always"}],
            },
        },
    )
    assert workflow.status_code == 201

    run = client.post(
        f"/workflows/{workflow.json()['id']}/runs",
        json={"input": "Calculate 2 + 3 * 4", "execute_async": False},
    )
    assert run.status_code == 201

    events = client.get(f"/runs/{run.json()['id']}/events")
    event_types = {event["event_type"] for event in events.json()}
    assert "agent_tool_call_started" in event_types
    assert "agent_tool_call_finished" in event_types

