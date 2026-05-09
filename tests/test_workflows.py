def test_template_workflow_executes_and_persists_messages_and_events(client):
    workflow_response = client.post(
        "/templates/research-writer/instantiate",
        json={"name": "Demo Research Workflow"},
    )
    assert workflow_response.status_code == 201
    workflow_id = workflow_response.json()["id"]

    run_response = client.post(
        f"/workflows/{workflow_id}/runs",
        json={"input": "Explain vector memory choices.", "execute_async": False},
    )
    assert run_response.status_code == 201
    run = run_response.json()
    assert run["status"] == "succeeded"
    assert run["output"]
    assert run["token_usage"]["prompt_tokens"] > 0

    messages = client.get(f"/runs/{run['id']}/messages")
    assert messages.status_code == 200
    assert len(messages.json()) >= 3
    assert {message["channel"] for message in messages.json()} == {"internal"}

    events = client.get(f"/runs/{run['id']}/events")
    assert events.status_code == 200
    event_types = {event["event_type"] for event in events.json()}
    assert "run_started" in event_types
    assert "model_call_started" in event_types
    assert "run_succeeded" in event_types
