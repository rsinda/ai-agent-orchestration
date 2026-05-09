from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class MemoryRecordInput:
    content: str
    agent_id: str | None = None
    workflow_id: str | None = None
    run_id: str | None = None
    user_id: str | None = None
    memory_scope: str = "workflow"
    memory_type: str = "message"
    source_message_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryHitResult:
    id: str
    content: str
    score: float
    agent_id: str | None
    workflow_id: str | None
    run_id: str | None
    user_id: str | None
    memory_scope: str
    memory_type: str
    metadata: dict[str, Any]
    created_at: datetime


class VectorMemoryStore(ABC):
    @abstractmethod
    def remember(self, memory: MemoryRecordInput) -> str:
        raise NotImplementedError

    @abstractmethod
    def recall(self, query: str, filters: dict[str, Any] | None = None, limit: int = 5) -> list[MemoryHitResult]:
        raise NotImplementedError

    @abstractmethod
    def delete_scope(self, scope: dict[str, Any]) -> None:
        raise NotImplementedError

