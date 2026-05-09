def test_telegram_inbound_starts_default_workflow_run(client):
    workflow_response = client.post("/templates/support-triage/instantiate", json={})
    assert workflow_response.status_code == 201
    workflow_id = workflow_response.json()["id"]

    connect = client.post(
        "/channels/telegram/connect",
        json={
            "channel": "telegram",
            "name": "Demo Bot",
            "default_workflow_id": workflow_id,
        },
    )
    assert connect.status_code == 201

    inbound = client.post(
        "/channels/telegram/inbound",
        json={
            "update_id": 123,
            "message": {
                "text": "I need help resetting my account",
                "chat": {"id": 456},
            },
        },
    )
    assert inbound.status_code == 200
    body = inbound.json()
    assert body["status"] == "succeeded"
    assert body["output"]

    messages = client.get(f"/runs/{body['run_id']}/messages")
    assert messages.status_code == 200
    channels = {message["channel"] for message in messages.json()}
    assert "telegram" in channels
    assert "internal" in channels
