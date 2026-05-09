from typing import Any

from sqlalchemy.orm import Session

from backend.app.db.models import MemoryRecord
from backend.app.memory.base import (
    MemoryHitResult,
    MemoryRecordInput,
    VectorMemoryStore,
)
from backend.app.memory.embeddings import (
    LocalEmbeddingService,
    cosine_similarity,
    get_embedding_service,
)


class PgVectorMemoryStore(VectorMemoryStore):
    """Default memory adapter.

    The storage model is portable for SQLite tests and Postgres demos. In a pgvector-backed
    deployment, this adapter is the boundary where vector SQL can replace the Python scorer.
    """

    filterable_fields = {
        "agent_id",
        "workflow_id",
        "run_id",
        "user_id",
        "memory_scope",
        "memory_type",
    }

    def __init__(
        self, db: Session, embeddings: LocalEmbeddingService | None = None
    ) -> None:
        self.db = db
        self.embeddings = embeddings or get_embedding_service()

    def remember(self, memory: MemoryRecordInput) -> str:
        record = MemoryRecord(
            agent_id=memory.agent_id,
            workflow_id=memory.workflow_id,
            run_id=memory.run_id,
            user_id=memory.user_id,
            memory_scope=memory.memory_scope,
            memory_type=memory.memory_type,
            content=memory.content,
            embedding=self.embeddings.embed(memory.content),
            source_message_id=memory.source_message_id,
            meta=memory.metadata,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record.id

    def recall(
        self, query: str, filters: dict[str, Any] | None = None, limit: int = 5
    ) -> list[MemoryHitResult]:
        filters = filters or {}
        db_query = self.db.query(MemoryRecord)
        for field, value in filters.items():
            if field in self.filterable_fields and value is not None:
                db_query = db_query.filter(getattr(MemoryRecord, field) == value)
        query_embedding = self.embeddings.embed(query)
        scored = [
            (cosine_similarity(query_embedding, record.embedding or []), record)
            for record in db_query.all()
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            MemoryHitResult(
                id=record.id,
                content=record.content,
                score=score,
                agent_id=record.agent_id,
                workflow_id=record.workflow_id,
                run_id=record.run_id,
                user_id=record.user_id,
                memory_scope=record.memory_scope,
                memory_type=record.memory_type,
                metadata=record.meta or {},
                created_at=record.created_at,
            )
            for score, record in scored[:limit]
        ]

    def delete_scope(self, scope: dict[str, Any]) -> None:
        db_query = self.db.query(MemoryRecord)
        for field, value in scope.items():
            if field in self.filterable_fields and value is not None:
                db_query = db_query.filter(getattr(MemoryRecord, field) == value)
        db_query.delete(synchronize_session=False)
        self.db.commit()
