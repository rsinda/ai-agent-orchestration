from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.memory.base import MemoryRecordInput
from backend.app.memory.pgvector import PgVectorMemoryStore
from backend.app.schemas import MemoryHit, MemoryRecallRequest, MemoryRecordCreate

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("/remember", status_code=status.HTTP_201_CREATED)
def remember(payload: MemoryRecordCreate, db: Session = Depends(get_db)) -> dict[str, str]:
    memory_id = PgVectorMemoryStore(db).remember(MemoryRecordInput(**payload.model_dump()))
    return {"id": memory_id}


@router.post("/recall", response_model=list[MemoryHit])
def recall(payload: MemoryRecallRequest, db: Session = Depends(get_db)):
    return PgVectorMemoryStore(db).recall(payload.query, payload.filters, payload.limit)

