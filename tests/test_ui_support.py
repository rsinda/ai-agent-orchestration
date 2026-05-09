def test_recent_runs_endpoint_lists_runs(client):
    workflow_response = client.post("/templates/support-triage/instantiate", json={})
    workflow_id = workflow_response.json()["id"]

    run_response = client.post(
        f"/workflows/{workflow_id}/runs",
        json={"input": "Need login help", "execute_async": False},
    )
    assert run_response.status_code == 201

    runs = client.get("/runs?limit=5")
    assert runs.status_code == 200
    assert runs.json()[0]["id"] == run_response.json()["id"]


def test_telegram_status_reports_binding_state(client):
    initial = client.get("/channels/telegram/status")
    assert initial.status_code == 200
    assert initial.json()["connected"] is False

    workflow_response = client.post("/templates/support-triage/instantiate", json={})
    workflow_id = workflow_response.json()["id"]
    connect = client.post(
        "/channels/telegram/connect",
        json={
            "channel": "telegram",
            "name": "UI Bot",
            "default_workflow_id": workflow_id,
        },
    )
    assert connect.status_code == 201

    status = client.get("/channels/telegram/status")
    assert status.status_code == 200
    assert status.json()["connected"] is True
    assert status.json()["default_workflow_id"] == workflow_id
