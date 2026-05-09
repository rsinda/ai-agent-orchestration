import asyncio
import contextlib
import logging
from typing import Any

import httpx
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.db.models import ChannelBinding, Message
from backend.app.db.session import SessionLocal
from backend.app.runtime.executor import RuntimeExecutor

logger = logging.getLogger(__name__)


class TelegramChannel:
    def __init__(self, db: Session) -> None:
        self.db = db

    async def handle_update(self, update: dict[str, Any]) -> dict[str, Any]:
        message = update.get("message") or update.get("edited_message") or {}
        text = message.get("text") or ""
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id", ""))
        if not text or not chat_id:
            return {"ignored": True, "reason": "No text chat message found."}

        binding = (
            self.db.query(ChannelBinding)
            .filter(ChannelBinding.channel == "telegram")
            .order_by(ChannelBinding.created_at.desc())
            .first()
        )
        if binding is None or not binding.default_workflow_id:
            return {"ignored": True, "reason": "Telegram channel is not connected to a workflow."}

        executor = RuntimeExecutor(self.db)
        run = executor.create_run(binding.default_workflow_id, text, user_id=chat_id)
        self.db.add(
            Message(
                run_id=run.id,
                workflow_id=run.workflow_id,
                sender_id=f"telegram:{chat_id}",
                recipient_id="workflow",
                channel="telegram",
                content=text,
                meta={"update_id": update.get("update_id")},
            )
        )
        self.db.commit()
        await executor.execute_run(run.id)
        self.db.refresh(run)

        token = binding.config.get("bot_token") or get_settings().telegram_bot_token
        if token and run.output:
            await self.send_message(token, chat_id, run.output)
        return {"run_id": run.id, "status": run.status, "output": run.output}

    async def send_message(self, token: str, chat_id: str, text: str) -> None:
        async with httpx.AsyncClient(timeout=20) as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text},
            )


class TelegramPollingService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._offset: int | None = None

    async def run_forever(self) -> None:
        while True:
            try:
                await self.poll_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Telegram polling failed.")
                await asyncio.sleep(5)

    async def poll_once(self) -> None:
        binding = self._latest_binding()
        token = self._token(binding)
        if binding is None or not binding.default_workflow_id or not token:
            await asyncio.sleep(5)
            return

        updates = await self._get_updates(token)
        for update in updates:
            update_id = update.get("update_id")
            if isinstance(update_id, int):
                self._offset = update_id + 1
            db = SessionLocal()
            try:
                await TelegramChannel(db).handle_update(update)
            finally:
                db.close()

    def _latest_binding(self) -> ChannelBinding | None:
        db = SessionLocal()
        try:
            return (
                db.query(ChannelBinding)
                .filter(ChannelBinding.channel == "telegram")
                .order_by(ChannelBinding.created_at.desc())
                .first()
            )
        finally:
            db.close()

    def _token(self, binding: ChannelBinding | None) -> str:
        if binding is not None:
            token = (binding.config or {}).get("bot_token")
            if token:
                return token
        return self.settings.telegram_bot_token

    async def _get_updates(self, token: str) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "timeout": 25,
            "allowed_updates": ["message", "edited_message"],
        }
        if self._offset is not None:
            params["offset"] = self._offset
        async with httpx.AsyncClient(timeout=35) as client:
            response = await client.get(f"https://api.telegram.org/bot{token}/getUpdates", params=params)
            response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            logger.warning("Telegram getUpdates returned non-ok response: %s", data)
            return []
        return data.get("result", [])


async def run_telegram_polling_until_cancelled() -> None:
    service = TelegramPollingService()
    with contextlib.suppress(asyncio.CancelledError):
        await service.run_forever()
