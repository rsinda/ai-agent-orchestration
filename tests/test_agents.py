def test_agent_crud(client):
    payload = {
        "name": "Researcher",
        "role": "researcher",
        "system_prompt": "Research facts.",
        "model": "mock-agent",
        "tools": ["memory"],
        "channels": [],
    }

    created = client.post("/agents", json=payload)
    assert created.status_code == 201
    agent_id = created.json()["id"]

    listed = client.get("/agents")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == agent_id

    updated = client.patch(f"/agents/{agent_id}", json={"name": "Lead Researcher"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Lead Researcher"

    deleted = client.delete(f"/agents/{agent_id}")
    assert deleted.status_code == 204
    assert client.get(f"/agents/{agent_id}").status_code == 404
