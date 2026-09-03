"""T06 production-boundary regression checks with no external services."""

from app.core.config import Settings
from app.main import should_seed_showcase
from app.modules.training.infrastructure.models import AICallLog


def test_normalized_production_environment_disables_demo_and_seed() -> None:
    """SEC-07: whitespace/casing must not make production behave like development."""
    production = Settings(
        app_env=" Production ",
        enable_demo_auth=True,
        seed_showcase_case=True,
        jwt_secret="T06 local test fixture, never a deployable credential",
    )

    assert production.is_production is True
    assert production.demo_auth_enabled is False
    assert should_seed_showcase(production) is False


def test_non_production_seed_remains_an_explicit_opt_in() -> None:
    development = Settings(app_env="development", seed_showcase_case=False)

    assert development.is_production is False
    assert should_seed_showcase(development) is False


def test_ai_audit_schema_excludes_prompt_and_student_answer_content() -> None:
    """SEC-05/06: audit rows retain operational metadata, not request/response bodies."""
    column_names = set(AICallLog.__table__.columns.keys())

    assert {"prompt", "answer", "request", "response", "messages", "content"}.isdisjoint(column_names)
    assert {"model_name", "prompt_version", "latency_ms", "fallback_used", "failure_reason"}.issubset(column_names)
