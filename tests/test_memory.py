from backend.app.memory.embeddings import cosine_similarity


def test_cosine_similarity_handles_real_embedding_vectors():
    assert cosine_similarity([1.1, 0.0, 0.2], [1.1, 0.0, 0.2]) == 1
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0
    assert cosine_similarity([], [1.0]) == 0
    assert cosine_similarity([1.0, 2.0], [1.0]) == 0


def test_memory_recall_is_scoped_by_filters(client):
    first = client.post(
        "/memory/remember",
        json={
            "agent_id": "agent-a",
            "workflow_id": "workflow-a",
            "user_id": "user-a",
            "content": "pgvector keeps relational and semantic memory together",
        },
    )
    assert first.status_code == 201
    second = client.post(
        "/memory/remember",
        json={
            "agent_id": "agent-b",
            "workflow_id": "workflow-a",
            "user_id": "user-a",
            "content": "telegram messages can trigger support triage",
        },
    )
    assert second.status_code == 201

    recall = client.post(
        "/memory/recall",
        json={
            "query": "semantic memory in postgres",
            "filters": {"agent_id": "agent-a", "workflow_id": "workflow-a"},
            "limit": 5,
        },
    )
    assert recall.status_code == 200
    hits = recall.json()
    assert len(hits) == 1
    assert hits[0]["agent_id"] == "agent-a"
    assert "pgvector" in hits[0]["content"]
