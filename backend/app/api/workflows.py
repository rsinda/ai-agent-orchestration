import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.models import Run, Workflow
from backend.app.db.session import SessionLocal, get_db
from backend.app.runtime.executor import RuntimeExecutor
from backend.app.schemas import RunCreate, RunRead, WorkflowCreate, WorkflowRead, WorkflowUpdate

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED)
def create_workflow(payload: WorkflowCreate, db: Session = Depends(get_db)) -> Workflow:
    workflow = Workflow(**payload.model_dump())
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


@router.get("", response_model=list[WorkflowRead])
def list_workflows(db: Session = Depends(get_db)) -> list[Workflow]:
    return db.query(Workflow).order_by(Workflow.created_at.desc()).all()


@router.get("/{workflow_id}", response_model=WorkflowRead)
def get_workflow(workflow_id: str, db: Session = Depends(get_db)) -> Workflow:
    workflow = db.get(Workflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    return workflow


@router.patch("/{workflow_id}", response_model=WorkflowRead)
def update_workflow(workflow_id: str, payload: WorkflowUpdate, db: Session = Depends(get_db)) -> Workflow:
    workflow = db.get(Workflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(workflow, key, value)
    db.commit()
    db.refresh(workflow)
    return workflow


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(workflow_id: str, db: Session = Depends(get_db)) -> None:
    workflow = db.get(Workflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    db.delete(workflow)
    db.commit()


@router.post("/{workflow_id}/runs", response_model=RunRead, status_code=status.HTTP_201_CREATED)
def create_run(
    workflow_id: str,
    payload: RunCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Run:
    try:
        run = RuntimeExecutor(db).create_run(workflow_id, payload.input, payload.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if payload.execute_async:
        background_tasks.add_task(_execute_run_task, run.id)
    else:
        asyncio.run(RuntimeExecutor(db).execute_run(run.id))
        db.refresh(run)
    return run


def _execute_run_task(run_id: str) -> None:
    db = SessionLocal()
    try:
        asyncio.run(RuntimeExecutor(db).execute_run(run_id))
    finally:
        db.close()

