"""Focused T05 contracts for learning application state and conflict recovery."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.modules.learning.application.records import LearningPlanRecord, LearningTaskAttemptRecord, LearningTaskRecord
from app.modules.learning.application.use_cases import LearningApplication
from app.shared.actor import Actor
from app.shared.errors import AppError, PersistenceConflict

NOW = datetime(2026, 8, 31, tzinfo=UTC)
ACTOR = Actor(7, "student-7", "student", "学生")


class Uow:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


def task(
    *,
    status: str = "pending",
    task_type: str = "micro_drill",
    previous: str | None = "completed",
    attempt=None,
    problem_id: int | None = None,
):
    return LearningTaskRecord(
        id=11,
        plan_id=3,
        position=2,
        task_type=task_type,
        dimension_id="test_selection",
        stage_id="tests",
        problem_id=problem_id if task_type != "micro_drill" else None,
        source_attempt_id=1,
        status=status,
        public_definition={},
        private_rubric={"criteria": []},
        blueprint_id=None,
        blueprint_digest=None,
        started_at=None,
        completed_at=None,
        previous_status=previous,
        attempt=attempt,
    )


def attempt(*, status: str = "in_progress"):
    return LearningTaskAttemptRecord(
        id=13,
        task_id=11,
        student_id=ACTOR.id,
        status=status,
        answer={"text": "原始答案"},
        score=None,
        evidence=(),
        feedback="",
        next_step="",
        model_name="fallback",
        prompt_version="practice-v1",
        fallback_used=True,
        failure_reason="disabled",
        created_at=NOW,
        assessed_at=None,
        public_definition={},
    )


def plan(*, status: str = "active", tasks=(), due_at=NOW):
    return LearningPlanRecord(
        id=3,
        student_id=ACTOR.id,
        status=status,
        source_assessment_id=2,
        target_dimension_ids=("test_selection",),
        due_at=due_at,
        generation_mode="deterministic",
        model_name="fallback",
        prompt_version="practice-v1",
        fallback_used=True,
        failure_reason="disabled",
        created_at=NOW,
        completed_at=NOW if status == "completed" else None,
        superseded_at=None,
        tasks=tasks,
    )


def application(repository, uow: Uow) -> LearningApplication:
    return LearningApplication(repository, uow, SimpleNamespace(generate=lambda *_: None), SimpleNamespace())


def test_learning_application_rejects_missing_or_locked_state_without_writes() -> None:
    repo = SimpleNamespace(
        find_active_plan=lambda *_: None,
        find_plan=lambda *_: None,
        find_task=lambda *_: task(previous="pending"),
        find_task_attempt=lambda *_: None,
    )
    uow = Uow()
    service = application(repo, uow)

    for operation in (
        lambda: service.current_plan(ACTOR),
        lambda: service.get_plan(ACTOR, 3),
        lambda: service.start_task(ACTOR, 11),
    ):
        with pytest.raises(AppError) as raised:
            operation()
        assert raised.value.code in {"RESOURCE_NOT_FOUND", "STATE_CONFLICT"}
    with pytest.raises(AppError) as raised:
        service.get_task_attempt(ACTOR, 13)
    assert raised.value.code == "RESOURCE_NOT_FOUND"
    assert uow.commits == uow.rollbacks == 0


def test_learning_application_preserves_idempotent_started_and_assessed_micro_attempts() -> None:
    started = attempt()
    assessed = attempt(status="assessed")
    repo = SimpleNamespace(
        find_task=lambda *_: task(status="in_progress", attempt=started),
        find_task_attempt=lambda *_: assessed,
    )
    uow = Uow()
    service = application(repo, uow)

    returned_task, returned_attempt = service.start_task(ACTOR, 11)
    assert returned_task.status == "in_progress" and returned_attempt.id == started.id
    assert service.submit_micro_task(ACTOR, assessed.id, {"text": "must not overwrite"}) is assessed
    assert uow.commits == uow.rollbacks == 0


def test_learning_application_recovers_a_racing_micro_start_and_assessment() -> None:
    started = attempt()
    winner = attempt(status="assessed")
    calls = {"task": 0}
    reads = {"attempt": 0}

    def mark_started(*_args):
        calls["task"] += 1
        raise PersistenceConflict()

    task_reads = 0

    def find_task(*_args):
        nonlocal task_reads
        task_reads += 1
        return task(status="pending" if task_reads == 1 else "in_progress", attempt=started)

    def find_task_attempt(*_args):
        reads["attempt"] += 1
        return started if reads["attempt"] == 1 else winner

    repo = SimpleNamespace(
        find_task=find_task,
        mark_task_started=mark_started,
        find_task_attempt=find_task_attempt,
        assess_micro_task=lambda *_: (_ for _ in ()).throw(PersistenceConflict()),
    )
    uow = Uow()
    service = application(repo, uow)

    _task, recovered = service.start_task(ACTOR, 11)
    assert recovered is started
    returned = service.submit_micro_task(ACTOR, started.id, {"text": "competing answer"})
    assert returned is winner
    assert winner.answer == {"text": "原始答案"}
    assert calls["task"] == 1 and uow.rollbacks == 2 and reads["attempt"] == 2


def test_learning_application_reports_conflict_when_racing_assessment_cannot_be_recovered() -> None:
    current = attempt()
    repo = SimpleNamespace(
        find_task=lambda *_: task(status="in_progress", attempt=current),
        find_task_attempt=lambda *_: current,
        assess_micro_task=lambda *_: (_ for _ in ()).throw(PersistenceConflict()),
    )
    uow = Uow()
    with pytest.raises(AppError) as raised:
        application(repo, uow).submit_micro_task(ACTOR, current.id, {"text": "answer"})
    assert raised.value.code == "STATE_CONFLICT" and raised.value.status_code == 409
    assert current.answer == {"text": "原始答案"} and current.status == "in_progress"
    assert uow.commits == 0 and uow.rollbacks == 1


def test_learning_application_covers_case_task_transitions_and_assessment_guards() -> None:
    active_plan = plan(tasks=(task(status="completed"),))
    source_attempt = SimpleNamespace(learning_task_id=11, id=31, problem=SimpleNamespace(id=99, difficulty="easy"))
    source = SimpleNamespace(attempt=source_attempt, assessment=SimpleNamespace(id=44, dimensions=()))
    completed = task(status="completed", previous="completed", task_type="focused_retry")
    retry = task(previous="completed", task_type="focused_retry", problem_id=99)
    case_attempt = object()
    repo = SimpleNamespace(
        find_source=lambda *_: source,
        mark_task_completed=lambda *_: None,
        find_active_plan=lambda *_: active_plan,
        find_task=lambda _student, task_id: completed if task_id == 11 else retry,
        find_case_attempt_for_task=lambda *_: case_attempt,
        mark_task_started=lambda *_: retry,
    )
    case_ports = SimpleNamespace(get=lambda *_: case_attempt, start=lambda *_: case_attempt)
    uow = Uow()
    service = LearningApplication(repo, uow, SimpleNamespace(generate=lambda *_: None), case_ports)

    assert service.ensure_for_case_completion(ACTOR, 31) is active_plan
    assert uow.commits == 1
    with pytest.raises(AppError) as raised:
        service.ensure_for_assessment(ACTOR, 31)
    assert raised.value.code == "STATE_CONFLICT"
    with pytest.raises(AppError) as raised:
        service.start_task(ACTOR, 11)
    assert raised.value.code == "STATE_CONFLICT"

    started, returned = service.start_task(ACTOR, 12)
    assert started is retry and returned is case_attempt
    assert uow.commits == 2

    retry_without_problem = task(previous="completed", task_type="focused_retry")
    repo.find_task = lambda _student, task_id: retry_without_problem if task_id == 12 else completed
    with pytest.raises(AppError) as raised:
        service.start_task(ACTOR, 12)
    assert raised.value.code == "RESOURCE_NOT_FOUND"


def test_learning_application_handles_non_micro_start_conflicts_and_missing_state() -> None:
    retry = task(previous="completed", task_type="focused_retry", problem_id=99)
    conflict = AppError("UPSTREAM", "upstream failed", 502)
    reads = {"task": 0}

    def find_task(*_args):
        reads["task"] += 1
        return retry

    repo = SimpleNamespace(
        find_task=find_task,
        find_case_attempt_for_task=lambda *_: None,
        mark_task_started=lambda *_: (_ for _ in ()).throw(PersistenceConflict()),
    )
    ports = SimpleNamespace(start=lambda *_: object(), get=lambda *_: object())
    uow = Uow()
    with pytest.raises(AppError) as raised:
        LearningApplication(repo, uow, SimpleNamespace(generate=lambda *_: None), ports).start_task(ACTOR, 11)
    assert raised.value.code == "STATE_CONFLICT" and uow.rollbacks == 1

    repo.find_task = lambda *_: None
    with pytest.raises(AppError) as raised:
        application(repo, uow).start_task(ACTOR, 11)
    assert raised.value.code == "RESOURCE_NOT_FOUND"

    repo.find_task = lambda *_: retry
    repo.mark_task_started = lambda *_: (_ for _ in ()).throw(conflict)
    with pytest.raises(AppError) as raised:
        LearningApplication(repo, uow, SimpleNamespace(generate=lambda *_: None), ports).start_task(ACTOR, 11)
    assert raised.value.code == "UPSTREAM"


def test_learning_application_completes_plans_and_recovers_notification_paths() -> None:
    complete = plan(status="active", tasks=(task(status="completed", previous="completed"),))
    winner = plan(status="completed", tasks=(task(status="completed", previous="completed"),))
    notifications: list[object] = []
    repo = SimpleNamespace(
        find_plan=lambda *_: complete,
        complete_plan=lambda *_: winner,
        add_notification=lambda *args: notifications.append(args),
    )
    uow = Uow()
    service = application(repo, uow)
    assert service.complete_plan(ACTOR, 3) is winner
    assert len(notifications) == 1 and uow.commits == 1

    repo.complete_plan = lambda *_: (_ for _ in ()).throw(PersistenceConflict())
    repo.find_plan = lambda *_: complete
    reads = {"count": 0}

    def find_after_conflict(*_args):
        reads["count"] += 1
        return complete if reads["count"] == 1 else winner

    repo.find_plan = find_after_conflict
    assert service.complete_plan(ACTOR, 3) is winner
    assert uow.rollbacks == 1

    repo.find_plan = lambda *_: complete
    with pytest.raises(AppError) as raised:
        service.complete_plan(ACTOR, 3)
    assert raised.value.code == "STATE_CONFLICT"

    repo.complete_plan = lambda *_: (_ for _ in ()).throw(RuntimeError("db"))
    with pytest.raises(AppError) as raised:
        service.complete_plan(ACTOR, 3)
    assert raised.value.code == "SERVICE_ERROR" and uow.rollbacks == 3


def test_learning_application_exposes_notification_profile_and_source_guards() -> None:
    due = plan(tasks=(task(status="completed", previous="completed"),), due_at=NOW)
    profile = SimpleNamespace(active_plan=due)
    refreshed = SimpleNamespace(active_plan=None)
    read: list[object] = []
    repo = SimpleNamespace(
        list_notifications=lambda *args: (args,),
        unread_count=lambda *_: 2,
        mark_notification_read=lambda *_: None,
        mark_all_notifications_read=lambda *_: 3,
        profile=lambda *_: profile if not read else refreshed,
        add_notification=lambda *args: read.append(args),
        mark_task_completed=lambda *_: None,
        find_source=lambda *_: None,
    )
    uow = Uow()
    service = application(repo, uow)
    assert service.notifications(ACTOR, True, 10)[0][1:] == (True, 10)
    assert service.unread_count(ACTOR) == 2
    service.mark_notification_read(ACTOR, 9)
    assert service.mark_all_notifications_read(ACTOR) == 3
    assert service.profile(ACTOR) is refreshed and read
    service.mark_task_completed(ACTOR, 11)
    with pytest.raises(AppError) as raised:
        service.ensure_for_case_completion(ACTOR, 100)
    assert raised.value.code == "RESOURCE_NOT_FOUND"


def test_learning_application_rejects_wrong_task_type_and_incomplete_or_completed_plans() -> None:
    incomplete = plan(tasks=(task(status="pending"),))
    finished = plan(status="completed", tasks=(task(status="completed"),))
    repo = SimpleNamespace(
        find_task_attempt=lambda *_: attempt(),
        find_task=lambda *_: task(task_type="focused_retry"),
        find_plan=lambda _student, plan_id: incomplete if plan_id == 3 else finished,
    )
    uow = Uow()
    service = application(repo, uow)

    with pytest.raises(AppError, match="STATE_CONFLICT"):
        service.submit_micro_task(ACTOR, 13, {"text": "wrong type"})
    with pytest.raises(AppError, match="STATE_CONFLICT"):
        service.complete_plan(ACTOR, 3)
    repo.find_plan = lambda *_: finished
    assert service.complete_plan(ACTOR, 4) is finished
    assert uow.commits == uow.rollbacks == 0
