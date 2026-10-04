"""Case assessment concurrency and the retired independent-case plan boundary.

T44 route claims, frozen tests and submission transactions are covered by
test_t44_learning_routes.
"""

from __future__ import annotations

from threading import Barrier, Lock, Thread

import pytest
from sqlalchemy import func, select

from app.db import SessionLocal
from app.modules.identity.infrastructure.models import User
from app.modules.learning.infrastructure.models import LearningPlan
from app.modules.training.application.records import AssessmentGenerationResult, AttemptRecord
from app.modules.training.application.use_cases import TrainingApplication
from app.modules.training.infrastructure.ai_gateway import CaseAiGateway
from app.modules.training.infrastructure.models import AICallLog, CaseAssessment, CaseAttempt
from app.modules.training.infrastructure.repositories import SqlAlchemyTrainingRepository
from app.platform.transactions import SqlAlchemyUnitOfWork
from app.shared.actor import Actor

pytestmark = pytest.mark.seed_showcase
CALL_COUNTER_LOCK = Lock()


class StaticAssessmentGateway:
    def __init__(self, barrier: Barrier | None = None, calls: list[int] | None = None) -> None:
        self._barrier = barrier
        self._calls = calls

    def assess(self, _attempt: AttemptRecord) -> AssessmentGenerationResult:
        if self._calls is not None:
            with CALL_COUNTER_LOCK:
                self._calls.append(1)
        if self._barrier is not None:
            self._barrier.wait(timeout=15)
        return AssessmentGenerationResult(
            candidates=(),
            fallback_used=True,
            failure_reason="test-static",
            model_name="deterministic-fallback",
            prompt_version="test-v1",
            latency_ms=0,
        )


class CountingTrainingRepository(SqlAlchemyTrainingRepository):
    def __init__(self, session, assessment_reads: list[int]) -> None:
        super().__init__(session)
        self._assessment_reads = assessment_reads

    def find_assessment(self, student_id: int, attempt_id: int):
        with CALL_COUNTER_LOCK:
            self._assessment_reads.append(1)
        return super().find_assessment(student_id, attempt_id)


def _login(client, role: str, external_id: str) -> str:
    response = client.post(
        "/auth/demo-login",
        json={"role": role, "external_id": external_id, "nickname": role, "avatar_url": ""},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _case_id(client) -> int:
    token = _login(client, "teacher", "t04_concurrency_teacher")
    response = client.get("/problems", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    return next(item["id"] for item in response.json() if item["content_type"] == "guided_case")


def _prepare_completed_source(client, external_id: str) -> tuple[int, int]:
    token = _login(client, "student", external_id)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(f"/problems/{_case_id(client)}/attempts", headers=headers, json={})
    assert response.status_code == 200
    attempt_id = response.json()["id"]
    answers = (
        ("history", {"stage_id": "history", "summary": "发热", "key_findings": ["发热"]}),
        ("problem_representation", {"stage_id": "problem_representation", "summary": "急性发热咳嗽"}),
        ("differential", {"stage_id": "differential", "items": [{"diagnosis": "肺炎"}, {"diagnosis": "病毒感染"}]}),
        (
            "tests",
            {"stage_id": "tests", "items": [{"test_name": "影像", "rationale": "评估", "priority": "necessary"}]},
        ),
        (
            "management",
            {
                "stage_id": "management",
                "items": [{"action": "评估氧合", "rationale": "安全"}],
                "safety_considerations": [],
            },
        ),
    )
    for stage_id, answer in answers:
        assert (
            client.post(
                f"/attempts/{attempt_id}/stages/{stage_id}/submit", headers=headers, json={"answer": answer}
            ).status_code
            == 200
        )
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.external_id == external_id))
        assert user is not None
        attempt = session.get(CaseAttempt, attempt_id)
        assert attempt is not None and attempt.status == "completed"
        assert session.scalar(select(func.count(CaseAssessment.id)).where(CaseAssessment.attempt_id == attempt_id)) == 0
        return user.id, attempt_id


def test_two_sessions_race_assessment_creation_converges(client) -> None:
    student_id, attempt_id = _prepare_completed_source(client, "t04_race_assessment")
    barrier = Barrier(2)
    assessment_calls: list[int] = []
    assessment_reads: list[int] = []
    result_ids: list[int] = []
    errors: list[BaseException] = []

    def worker() -> None:
        with SessionLocal() as session:
            user = session.get(User, student_id)
            assert user is not None
            application = TrainingApplication(
                repository=CountingTrainingRepository(session, assessment_reads),
                uow=SqlAlchemyUnitOfWork(session),
                patient_gateway=CaseAiGateway(),
                assessment_gateway=StaticAssessmentGateway(barrier, assessment_calls),
            )
            try:
                result_ids.append(application.complete(Actor.from_user(user), attempt_id).id)
            except BaseException as error:
                errors.append(error)

    threads = [Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=45)
        assert not thread.is_alive()
    assert not errors
    assert len(result_ids) == 2 and len(set(result_ids)) == 1
    assert len(assessment_calls) == 2 and len(assessment_reads) == 1
    with SessionLocal() as session:
        assert session.scalar(select(func.count(CaseAssessment.id)).where(CaseAssessment.attempt_id == attempt_id)) == 1
        assert (
            session.scalar(
                select(func.count(AICallLog.id)).where(
                    AICallLog.attempt_id == attempt_id, AICallLog.task == "assessment"
                )
            )
            == 1
        )


def test_concurrent_legacy_plan_requests_cannot_turn_independent_case_into_teacher_work(client) -> None:
    student_id, attempt_id = _prepare_completed_source(client, "t43_independent_case_race")
    with SessionLocal() as session:
        user = session.get(User, student_id)
        assert user is not None
        TrainingApplication(
            repository=SqlAlchemyTrainingRepository(session),
            uow=SqlAlchemyUnitOfWork(session),
            patient_gateway=CaseAiGateway(),
            assessment_gateway=StaticAssessmentGateway(),
        ).complete(Actor.from_user(user), attempt_id)
    token = _login(client, "student", "t43_independent_case_race")
    headers = {"Authorization": f"Bearer {token}"}
    barrier = Barrier(2)
    statuses: list[int] = []
    errors: list[BaseException] = []

    def request_plan() -> None:
        try:
            barrier.wait(timeout=15)
            statuses.append(client.post(f"/attempts/{attempt_id}/learning-plan", headers=headers).status_code)
        except BaseException as error:
            errors.append(error)

    threads = [Thread(target=request_plan) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=45)
        assert not thread.is_alive()
    assert not errors
    assert statuses == [409, 409]
    with SessionLocal() as session:
        assert session.scalar(select(func.count(LearningPlan.id)).where(LearningPlan.student_id == student_id)) == 0
