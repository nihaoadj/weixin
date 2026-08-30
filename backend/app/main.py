from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    ai,
    analytics,
    auth,
    case_attempts,
    classes,
    conversations,
    medical_review,
    personalized,
    problems,
    reports,
)
from app.core.config import get_settings

settings = get_settings()


def validate_runtime_settings() -> None:
    if settings.app_env.strip().lower() == "production" and (
        settings.jwt_secret == "change-me-in-local-env" or len(settings.jwt_secret) < 32
    ):
        raise RuntimeError("生产环境必须设置至少 32 位随机 JWT_SECRET")


validate_runtime_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.seed_showcase_case and settings.app_env != "production":
        from app.db import SessionLocal
        from app.services.case_seed import seed_showcase_case

        db = SessionLocal()
        try:
            seed_showcase_case(db)
        finally:
            db.close()
    yield


app = FastAPI(title="Medical QA API", version="0.1.0", lifespan=lifespan)

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
app.include_router(case_attempts.router)
app.include_router(classes.router)
app.include_router(medical_review.router)
app.include_router(problems.router)
app.include_router(analytics.router)
app.include_router(personalized.router)
