"""Compatibility facade for AI ports owned by bounded contexts.

Routes and application services use the module gateways directly.  This file
keeps the established import paths for seed tooling and focused tests without
owning prompt, fallback, persistence, or transaction rules.
"""

from __future__ import annotations

import httpx

from app.modules.content.infrastructure.draft_generator import DeterministicCaseDraftGenerator
from app.modules.learning.infrastructure.practice_generator import PracticeDefinitionGenerator
from app.modules.training.application.records import AttemptRecord
from app.modules.training.infrastructure.ai_gateway import CaseAiGateway, call_structured
from app.modules.training.infrastructure.ai_schemas import AIAssessmentDimension, AIAssessmentResponse
from app.modules.training.infrastructure.models import CaseAttempt
from app.modules.training.infrastructure.repositories import SqlAlchemyTrainingRepository
from app.platform.ai import AICallResult

PRACTICE_PROMPT_VERSION = "practice-v1"


def generate_draft(_db, topic: str, learner_level: str, objectives: list[str], _user_id: int) -> dict[str, object]:
    result = DeterministicCaseDraftGenerator().generate(topic, learner_level, objectives, _user_id)
    return {
        **result.payload,
        "generation_mode": result.generation_mode,
        "safety_notice": result.safety_notice,
    }


def _record(db, attempt: CaseAttempt | AttemptRecord) -> AttemptRecord:
    if isinstance(attempt, AttemptRecord):
        return attempt
    record = SqlAlchemyTrainingRepository(db).find_attempt(attempt.student_id, attempt.id)
    if record is None:
        raise ValueError("case attempt not found")
    return record


def patient_reply(db, attempt: CaseAttempt | AttemptRecord, content: str) -> tuple[str, list[str], str]:
    result = CaseAiGateway().reply(_record(db, attempt), content)
    return result.reply, list(result.revealed_fact_ids), result.response_mode


def ai_assessment(db, attempt: CaseAttempt | AttemptRecord) -> AIAssessmentResponse | None:
    result = CaseAiGateway().assess(_record(db, attempt))
    if result.fallback_used:
        return None
    return AIAssessmentResponse(
        dimensions=[
            AIAssessmentDimension(
                dimension_id=item.dimension_id,
                score=item.score,
                evidence=list(item.evidence),
                feedback=item.feedback,
                next_step=item.next_step,
            )
            for item in result.candidates
        ]
    )


def generate_practice_definition(
    _db,
    _student_id: int,
    _task_id: int,
    blueprint: dict[str, object],
    weakness_summary: str,
) -> tuple[dict[str, object], bool, str | None, str, str]:
    result = PracticeDefinitionGenerator().generate(blueprint, weakness_summary)
    return (
        result.public_definition,
        result.fallback_used,
        result.failure_reason,
        result.model_name,
        result.prompt_version,
    )


__all__ = [
    "AICallResult",
    "PRACTICE_PROMPT_VERSION",
    "ai_assessment",
    "call_structured",
    "generate_draft",
    "generate_practice_definition",
    "httpx",
    "patient_reply",
]
