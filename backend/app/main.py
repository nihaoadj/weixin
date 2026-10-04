from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException

# Canonical model registration must precede the test fixture's create_all as
# well as Alembic; individual API modules must not import ORM models for this.
from app.bootstrap import model_registry as _model_registry  # noqa: F401
from app.core.config import Settings, get_settings
from app.errors import (
    ErrorResponse,
    app_error_handler,
    http_exception_handler,
    unexpected_exception_handler,
    validation_exception_handler,
)
from app.modules.analytics.api import analytics
from app.modules.classroom.api import classes
from app.modules.content.api import knowledge, medical_review, problems, question_bank
from app.modules.identity.api import auth
from app.modules.learning.api import classroom_packages, knowledge_review, personalized, study
from app.modules.learning.api import routes as learning_routes
from app.modules.pbl.api import router as pbl_router
from app.modules.qa.api import ai, conversations, student_questions
from app.modules.reports.api import reports
from app.modules.training.api import case_attempts
from app.shared.errors import AppError

settings = get_settings()


def validate_runtime_settings() -> None:
    if settings.is_production and (settings.jwt_secret == "change-me-in-local-env" or len(settings.jwt_secret) < 32):
        raise RuntimeError("生产环境必须设置至少 32 位随机 JWT_SECRET")
    if settings.pbl_ai_enabled:
        # Only configuration assembly runs here; gateways perform no network I/O
        # until a student message is submitted.
        from app.modules.pbl.wiring import _gateway

        _gateway()


validate_runtime_settings()


def should_seed_showcase(runtime_settings: Settings) -> bool:
    return runtime_settings.seed_showcase_case and not runtime_settings.is_production


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if should_seed_showcase(settings):
        from app.bootstrap.seed import seed_showcase_case
        from app.db import SessionLocal

        db = SessionLocal()
        try:
            seed_showcase_case(db)
        finally:
            db.close()
    yield


app = FastAPI(
    title="Medical QA API",
    version="0.1.0",
    lifespan=lifespan,
    responses={code: {"model": ErrorResponse} for code in (400, 401, 403, 404, 409, 422, 500, 503)},
)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unexpected_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(ai.router)
app.include_router(conversations.router)
app.include_router(reports.router)
app.include_router(student_questions.router)
app.include_router(case_attempts.router)
app.include_router(classes.router)
app.include_router(medical_review.router)
app.include_router(medical_review.question_router)
app.include_router(question_bank.router)
app.include_router(problems.router)
app.include_router(knowledge.router)
app.include_router(analytics.router)
app.include_router(analytics.classroom_progress_router)
app.include_router(personalized.router)
app.include_router(knowledge_review.router)
app.include_router(study.router)
app.include_router(classroom_packages.router)
app.include_router(learning_routes.router)
app.include_router(pbl_router)
