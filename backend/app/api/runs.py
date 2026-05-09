import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.db.models import Message, Run, RunEvent
from backend.app.db.session import get_db
from backend.app.runtime.event_bus import event_bus
from backend.app.schemas import MessageRead, RunEventRead, RunRead

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("", response_model=list[RunRead])
def list_runs(limit: int = 25, db: Session = Depends(get_db)) -> list[Run]:
    limit = max(1, min(limit, 100))
    return db.query(Run).order_by(Run.created_at.desc()).limit(limit).all()


@router.get("/{run_id}", response_model=RunRead)
def get_run(run_id: str, db: Session = Depends(get_db)) -> Run:
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    return run


@router.get("/{run_id}/messages", response_model=list[MessageRead])
def list_run_messages(run_id: str, db: Session = Depends(get_db)) -> list[Message]:
    _require_run(db, run_id)
    return db.query(Message).filter(Message.run_id == run_id).order_by(Message.created_at.asc()).all()


@router.get("/{run_id}/events", response_model=list[RunEventRead])
def list_run_events(run_id: str, db: Session = Depends(get_db)) -> list[RunEvent]:
    _require_run(db, run_id)
    return db.query(RunEvent).filter(RunEvent.run_id == run_id).order_by(RunEvent.created_at.asc()).all()


@router.get("/{run_id}/stream")
async def stream_run(run_id: str, db: Session = Depends(get_db)) -> StreamingResponse:
    _require_run(db, run_id)

    async def event_stream():
        async for event in event_bus.subscribe(run_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _require_run(db: Session, run_id: str) -> Run:
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    return run
