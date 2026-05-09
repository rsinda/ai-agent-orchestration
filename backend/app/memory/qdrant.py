from typing import Any

from backend.app.memory.base import MemoryHitResult, MemoryRecordInput, VectorMemoryStore


class QdrantMemoryStore(VectorMemoryStore):
    def remember(self, memory: MemoryRecordInput) -> str:
        raise NotImplementedError("Qdrant adapter is planned behind the VectorMemoryStore interface.")

    def recall(self, query: str, filters: dict[str, Any] | None = None, limit: int = 5) -> list[MemoryHitResult]:
        raise NotImplementedError("Qdrant adapter is planned behind the VectorMemoryStore interface.")

    def delete_scope(self, scope: dict[str, Any]) -> None:
        raise NotImplementedError("Qdrant adapter is planned behind the VectorMemoryStore interface.")

