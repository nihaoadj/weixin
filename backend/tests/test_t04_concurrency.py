"""Concurrency and retry evidence for the training/learning transaction contracts."""

from __future__ import annotations

from threading import Barrier, Lock, Thread

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.modules.identity.infrastructure.models import User
from app.modules.learning.application.records import PracticeGenerationResult
from app.modules.learning.application.use_cases import LearningApplication
from app.modules.learning.infrastructure.models import (
    LearningPlan,
    LearningTask,
    LearningTaskAttempt,
    StudentNotification,
)
from app.modules.learning.infrastructure.repositories import SqlAlchemyLearningRepository
from app.modules.training.application.records import AssessmentGenerationResult, AttemptRecord
from app.modules.training.application.use_cases import TrainingApplication
from app.modules.training.infrastructure.ai_gateway import CaseAiGateway
from app.modules.training.infrastructure.models import AICallLog, CaseAssessment, CaseAttempt
from app.modules.training.infrastructure.repositories import SqlAlchemyTrainingRepository
from app.modules.training.public import CaseAttemptContract
from app.platform.transactions import SqlAlchemyUnitOfWork
from app.shared.actor import Actor
from app.shared.errors import AppError

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


class StaticPracticeGenerator:
    def __init__(self, barrier: Barrier | None = None, calls: list[int] | None = None) -> None:
        self._barrier = barrier
        self._calls = calls

    def generate(self, _blueprint: dict[str, object], _weakness_summary: str) -> PracticeGenerationResult:
        if self._calls is not None:
            with CALL_COUNTER_LOCK:
                self._calls.append(1)
        if self._barrier is not None:
            self._barrier.wait(timeout=15)
        return PracticeGenerationResult(
            public_definition={
                "title": "并发测试微训练",
                "context": "合成教学情境",
                "instruction": "列出证据并说明安全边界。",
                "answer_schema": "evidence_grid",
                "display_hints": [],
            },
            fallback_used=True,
            failure_reason="test-static",
            model_name="deterministic-fallback",
            prompt_version="practice-v1",
            latency_ms=0,
        )


class NoopCaseAttemptPort:
    def start(
        self, _actor: Actor, _problem_id: int, _retry_of_id: int | None, _learning_task_id: int
    ) -> CaseAttemptContract:
        raise AssertionError("case port is not used by this test")

    def get(self, _actor: Actor, _attempt_id: int) -> CaseAttemptContract:
        raise AssertionError("case port is not used by this test")


class BarrierTaskRepository(SqlAlchemyLearningRepository):
    def __init__(self, session: Session, barrier: Barrier, calls: list[int] | None = None) -> None:
        super().__init__(session)
        self._barrier = barrier
        self._calls = calls

    def mark_task_started(self, student_id: int, task_id: int, started_at):
        if self._calls is not None:
            with CALL_COUNTER_LOCK:
                self._calls.append(1)
        self._barrier.wait(timeout=15)
        return super().mark_task_started(student_id, task_id, started_at)


class CountingTrainingRepository(SqlAlchemyTrainingRepository):
    def __init__(self, session: Session, assessment_reads: list[int]) -> None:
        super().__init__(session)
        self._assessment_reads = assessment_reads

    def find_assessment(self, student_id: int, attempt_id: int):
        with CALL_COUNTER_LOCK:
            self._assessment_reads.append(1)
        return super().find_assessment(student_id, attempt_id)


class CountingLearningRepository(SqlAlchemyLearningRepository):
    def __init__(self, session: Session, plan_reads: list[int]) -> None:
        super().__init__(session)
        self._plan_reads = plan_reads

    def find_plan_by_assessment(self, student_id: int, assessment_id: int):
        with CALL_COUNTER_LOCK:
            self._plan_reads.append(1)
        return super().find_plan_by_assessment(student_id, assessment_id)


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
    attempt_response = client.post(f"/problems/{_case_id(client)}/attempts", headers=headers, json={})
    assert attempt_response.status_code == 200
    attempt_id = attempt_response.json()["id"]
    answers = (
        ("history", {"stage_id": "history", "summary": "发热", "key_findings": ["发热"]}),
        ("problem_representation", {"stage_id": "problem_representation", "summary": "急性发热咳嗽"}),
        (
            "differential",
            {"stage_id": "differential", "items": [{"diagnosis": "肺炎"}, {"diagnosis": "病毒感染"}]},
        ),
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
        response = client.post(
            f"/attempts/{attempt_id}/stages/{stage_id}/submit", headers=headers, json={"answer": answer}
        )
        assert response.status_code == 200

    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.external_id == external_id))
        assert user is not None
        attempt = session.scalar(select(CaseAttempt).where(CaseAttempt.id == attempt_id))
        assert attempt is not None
        assert attempt.status == "completed"
        assert session.scalar(select(func.count(CaseAssessment.id)).where(CaseAssessment.attempt_id == attempt_id)) == 0
        return user.id, attempt_id


def _assess_source(student_id: int, attempt_id: int) -> int:
    with SessionLocal() as session:
        user = session.get(User, student_id)
        assert user is not None
        assert session.scalar(select(func.count(CaseAssessment.id)).where(CaseAssessment.attempt_id == attempt_id)) == 0
        application = TrainingApplication(
            repository=SqlAlchemyTrainingRepository(session),
            uow=SqlAlchemyUnitOfWork(session),
            patient_gateway=CaseAiGateway(),
            assessment_gateway=StaticAssessmentGateway(),
        )
        return application.complete(Actor.from_user(user), attempt_id).id


def _prepare_assessed_source(client, external_id: str) -> tuple[int, int, int]:
    student_id, attempt_id = _prepare_completed_source(client, external_id)
    return student_id, attempt_id, _assess_source(student_id, attempt_id)

def test_two_sessions_race_assessment_creation_converges(client) -> None:
    student_id, attempt_id = _prepare_completed_source(client, "t04_race_assessment")
    with SessionLocal() as session:
        assert session.scalar(select(func.count(CaseAssessment.id)).where(CaseAssessment.attempt_id == attempt_id)) == 0
        assert session.scalar(
            select(func.count(AICallLog.id)).where(
                AICallLog.attempt_id == attempt_id, AICallLog.task == "assessment"
            )
        ) == 0

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
    assert errors == []
    assert len(result_ids) == 2
    assert len(set(result_ids)) == 1
    assert len(assessment_calls) == 2
    assert len(assessment_reads) == 1

    with SessionLocal() as session:
        assert session.scalar(select(func.count(CaseAssessment.id)).where(CaseAssessment.attempt_id == attempt_id)) == 1
        assert session.scalar(
            select(func.count(AICallLog.id)).where(
                AICallLog.attempt_id == attempt_id, AICallLog.task == "assessment"
            )
        ) == 1


def test_two_sessions_race_learning_plan_creation_converges(client) -> None:
    student_id, _attempt_id, assessment_id = _prepare_assessed_source(client, "t04_race_plan")
    with SessionLocal() as session:
        assert session.scalar(
            select(func.count(LearningPlan.id)).where(
                LearningPlan.student_id == student_id, LearningPlan.source_assessment_id == assessment_id
            )
        ) == 0
        assert session.scalar(
            select(func.count(AICallLog.id)).where(
                AICallLog.user_id == student_id, AICallLog.task == "practice_generation"
            )
        ) == 0

    barrier = Barrier(2)
    generation_calls: list[int] = []
    plan_reads: list[int] = []
    result_ids: list[int] = []
    errors: list[BaseException] = []

    def worker() -> None:
        with SessionLocal() as session:
            user = session.get(User, student_id)
            assert user is not None
            application = LearningApplication(
                repository=CountingLearningRepository(session, plan_reads),
                uow=SqlAlchemyUnitOfWork(session),
                practice_generator=StaticPracticeGenerator(barrier, generation_calls),
                case_attempts=NoopCaseAttemptPort(),
            )
            try:
                result_ids.append(application.ensure_for_assessment(Actor.from_user(user), _attempt_id).id)
            except BaseException as error:
                errors.append(error)

    threads = [Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=45)
        assert not thread.is_alive()
    assert errors == []
    assert len(result_ids) == 2
    assert len(set(result_ids)) == 1
    assert len(generation_calls) == 2
    assert len(plan_reads) == 3

    with SessionLocal() as session:
        assert session.scalar(
            select(func.count(LearningPlan.id)).where(
                LearningPlan.student_id == student_id, LearningPlan.source_assessment_id == assessment_id
            )
        ) == 1
        plan_id = result_ids[0]
        assert session.scalar(select(func.count(LearningTask.id)).where(LearningTask.plan_id == plan_id)) == 3
        assert session.scalar(
            select(func.count(StudentNotification.id)).where(
                StudentNotification.entity_id == plan_id, StudentNotification.type == "learning_plan_ready"
            )
        ) == 1
        assert session.scalar(
            select(func.count(AICallLog.id)).where(
                AICallLog.user_id == student_id, AICallLog.task == "practice_generation"
            )
        ) == 1


def test_two_sessions_race_micro_task_start_converges(client) -> None:
    _other_student_id, other_attempt_id = _prepare_completed_source(client, "t04_race_task_unassessed")
    student_id, attempt_id, assessment_id = _prepare_assessed_source(client, "t04_race_task")
    assert attempt_id != assessment_id
    with SessionLocal() as session:
        user = session.get(User, student_id)
        assert user is not None
        source = session.scalar(select(CaseAssessment).where(CaseAssessment.attempt_id == attempt_id))
        assert source is not None
        assert source.id == assessment_id
        assert (
            session.scalar(
                select(func.count(CaseAssessment.id)).where(CaseAssessment.attempt_id == other_attempt_id)
            )
            == 0
        )
        plan_app = LearningApplication(
            repository=SqlAlchemyLearningRepository(session),
            uow=SqlAlchemyUnitOfWork(session),
            practice_generator=StaticPracticeGenerator(),
            case_attempts=NoopCaseAttemptPort(),
        )
        plan = plan_app.ensure_for_assessment(Actor.from_user(user), attempt_id)
        first = session.scalar(select(LearningTask).where(LearningTask.plan_id == plan.id, LearningTask.position == 1))
        second = session.scalar(select(LearningTask).where(LearningTask.plan_id == plan.id, LearningTask.position == 2))
        assert first is not None and second is not None
        first.status = "completed"
        session.commit()
        task_id = second.id

    barrier = Barrier(2)
    task_start_calls: list[int] = []
    attempt_ids: list[int] = []
    errors: list[BaseException] = []

    with SessionLocal() as session:
        assert (
            session.scalar(
                select(func.count(LearningTaskAttempt.id)).where(LearningTaskAttempt.task_id == task_id)
            )
            == 0
        )

    def worker() -> None:
        with SessionLocal() as session:
            user = session.get(User, student_id)
            assert user is not None
            application = LearningApplication(
                repository=BarrierTaskRepository(session, barrier, task_start_calls),
                uow=SqlAlchemyUnitOfWork(session),
                practice_generator=StaticPracticeGenerator(),
                case_attempts=NoopCaseAttemptPort(),
            )
            try:
                _task, attempt = application.start_task(Actor.from_user(user), task_id)
                attempt_ids.append(attempt.id)
            except BaseException as error:
                errors.append(error)

    threads = [Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=45)
        assert not thread.is_alive()
    assert errors == []
    assert len(attempt_ids) == 2
    assert len(set(attempt_ids)) == 1
    assert len(task_start_calls) == 2
    with SessionLocal() as session:
        count = session.scalar(
            select(func.count(LearningTaskAttempt.id)).where(LearningTaskAttempt.task_id == task_id)
        )
        assert count == 1


def test_learning_plan_side_effect_failure_rolls_back_and_retry_is_idempotent(client, monkeypatch) -> None:
    student_id, attempt_id, _assessment_id = _prepare_assessed_source(client, "t04_retry_plan")
    with SessionLocal() as session:
        assert session.scalar(select(func.count(LearningPlan.id)).where(LearningPlan.student_id == student_id)) == 0
    original = SqlAlchemyLearningRepository.add_notification
    failed = False

    def fail_once(self, student_id: int, plan_id: int, kind: str, title: str, body: str):
        nonlocal failed
        if not failed:
            failed = True
            raise RuntimeError("injected notification failure")
        return original(self, student_id, plan_id, kind, title, body)

    monkeypatch.setattr(SqlAlchemyLearningRepository, "add_notification", fail_once)
    with SessionLocal() as session:
        user = session.get(User, student_id)
        assert user is not None
        application = LearningApplication(
            repository=SqlAlchemyLearningRepository(session),
            uow=SqlAlchemyUnitOfWork(session),
            practice_generator=StaticPracticeGenerator(),
            case_attempts=NoopCaseAttemptPort(),
        )
        with pytest.raises(AppError) as raised:
            application.ensure_for_assessment(Actor.from_user(user), attempt_id)
        assert raised.value.code == "SERVICE_ERROR"

    with SessionLocal() as session:
        assert session.scalar(select(func.count(LearningPlan.id)).where(LearningPlan.student_id == student_id)) == 0

    with SessionLocal() as session:
        user = session.get(User, student_id)
        assert user is not None
        application = LearningApplication(
            repository=SqlAlchemyLearningRepository(session),
            uow=SqlAlchemyUnitOfWork(session),
            practice_generator=StaticPracticeGenerator(),
            case_attempts=NoopCaseAttemptPort(),
        )
        plan = application.ensure_for_assessment(Actor.from_user(user), attempt_id)
        session.expunge_all()

    with SessionLocal() as session:
        assert session.scalar(select(func.count(LearningPlan.id)).where(LearningPlan.id == plan.id)) == 1
        assert session.scalar(
            select(func.count(StudentNotification.id)).where(
                StudentNotification.entity_id == plan.id, StudentNotification.type == "learning_plan_ready"
            )
        ) == 1
        assert session.scalar(
            select(func.count(AICallLog.id)).where(
                AICallLog.user_id == student_id, AICallLog.task == "practice_generation"
            )
        ) == 1
