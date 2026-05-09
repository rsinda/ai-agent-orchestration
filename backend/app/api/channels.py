from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.channels.telegram import TelegramChannel
from backend.app.core.config import get_settings
from backend.app.db.models import ChannelBinding, Workflow
from backend.app.db.session import get_db
from backend.app.schemas import ChannelBindingRead, ChannelConnectRequest

router = APIRouter(prefix="/channels", tags=["channels"])


@router.post("/telegram/connect", response_model=ChannelBindingRead, status_code=status.HTTP_201_CREATED)
def connect_telegram(payload: ChannelConnectRequest, db: Session = Depends(get_db)) -> ChannelBinding:
    if payload.default_workflow_id and db.get(Workflow, payload.default_workflow_id) is None:
        raise HTTPException(status_code=404, detail="Default workflow not found.")
    token = payload.bot_token or get_settings().telegram_bot_token
    binding = ChannelBinding(
        channel="telegram",
        name=payload.name,
        default_workflow_id=payload.default_workflow_id,
        config={"bot_token": token},
    )
    db.add(binding)
    db.commit()
    db.refresh(binding)
    return binding


@router.get("/telegram/status")
def telegram_status(db: Session = Depends(get_db)) -> dict:
    binding = (
        db.query(ChannelBinding)
        .filter(ChannelBinding.channel == "telegram")
        .order_by(ChannelBinding.created_at.desc())
        .first()
    )
    settings = get_settings()
    token = ""
    if binding is not None:
        token = (binding.config or {}).get("bot_token", "")
    token = token or settings.telegram_bot_token
    return {
        "connected": bool(binding and binding.default_workflow_id),
        "token_configured": bool(token),
        "polling_enabled": bool(token and binding and binding.default_workflow_id),
        "binding_id": binding.id if binding else None,
        "name": binding.name if binding else None,
        "default_workflow_id": binding.default_workflow_id if binding else None,
    }


@router.post("/telegram/inbound")
async def telegram_inbound(update: dict, db: Session = Depends(get_db)) -> dict:
    return await TelegramChannel(db).handle_update(update)
