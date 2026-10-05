"""FastAPI entrypoint:  uvicorn api.app:app --reload   (run `alembic upgrade head` first)."""
import uuid
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from api.deps import rate_limit, require_api_key
from api.routers import analysis, experiments, interviews, surveys
from config import settings
from db import session as dbs
from llm import LLMError
from services.errors import AppError
from utils.logging import get_logger, log_event

log = get_logger("api")


async def recover_interrupted_surveys() -> int:
    """A restart kills in-process jobs: surveys left 'running' become 'partial' so POST /run can resume them.
    (Single-instance assumption; with several instances this would move to a worker heartbeat.)"""
    from sqlalchemy import update
    from db.models import Survey
    try:
        async with dbs.session_scope() as s:
            res = await s.execute(update(Survey).where(Survey.status == "running").values(status="partial"))
            await s.commit()
            if res.rowcount:
                log_event(log, "interrupted_surveys_recovered", count=res.rowcount)
            return res.rowcount
    except SQLAlchemyError as e:  # DB not ready/migrated yet: don't block startup
        log_event(log, "recovery_skipped", level=30, error=type(e).__name__)
        return 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    dbs.get_engine()
    await recover_interrupted_surveys()
    yield
    await dbs.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Synthetic Persona Platform API", version="3.0.0", lifespan=lifespan)
    api = APIRouter(prefix="/api", dependencies=[Depends(require_api_key), Depends(rate_limit)])
    for r in (experiments.router, surveys.router, interviews.router, analysis.router):
        api.include_router(r)
    app.include_router(api)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    def err(status: int, code: str, message: str, request: Request):
        return JSONResponse(status_code=status, content={"error": {"code": code, "message": message,
                            "requestId": request.headers.get("x-request-id", uuid.uuid4().hex[:12])}})

    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):
        return err(exc.status_code, exc.code, exc.message, request)

    @app.exception_handler(LLMError)
    async def _llm_error(request: Request, exc: LLMError):
        log_event(log, "llm_error", level=40, kind=exc.kind, error=str(exc))
        return err(502 if exc.kind != "timeout" else 504, f"llm_{exc.kind}", "the language model could not complete the request; retry later", request)

    @app.exception_handler(SQLAlchemyError)
    async def _db_error(request: Request, exc: SQLAlchemyError):
        log_event(log, "database_error", level=40, error=type(exc).__name__)
        return err(503, "database_error", "database temporarily unavailable", request)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        log_event(log, "unhandled_error", level=40, error=repr(exc))
        return err(500, "internal_error", "internal server error", request)  # never leak stack traces

    return app


app = create_app()
