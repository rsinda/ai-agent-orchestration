from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas import TemplateInstantiateRequest, TemplateRead, WorkflowRead
from backend.app.templates.catalog import TEMPLATES, instantiate_template

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=list[TemplateRead])
def list_templates() -> list[TemplateRead]:
    return [TemplateRead(id=item.id, name=item.name, description=item.description) for item in TEMPLATES]


@router.post("/{template_id}/instantiate", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED)
def instantiate(template_id: str, payload: TemplateInstantiateRequest, db: Session = Depends(get_db)):
    try:
        return instantiate_template(db, template_id, payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

