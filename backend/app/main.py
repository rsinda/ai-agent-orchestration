from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI

from backend.app.api import agents, channels, memory, runs, templates, tools, workflows
from backend.app.channels.telegram import run_telegram_polling_until_cancelled
from backend.app.core.config import get_settings
from backend.app.db.session import init_db


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db()
        telegram_task = asyncio.create_task(run_telegram_polling_until_cancelled())
        try:
            yield
        finally:
            telegram_task.cancel()
            await telegram_task

    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(agents.router)
    app.include_router(workflows.router)
    app.include_router(runs.router)
    app.include_router(templates.router)
    app.include_router(tools.router)
    app.include_router(memory.router)
    app.include_router(channels.router)
    return app


app = create_app()
