import json
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from sqlalchemy import select

from app.bootstrap.seed import seed_showcase_case
from app.modules.classroom.infrastructure.models import ClassRoom
from app.modules.content.infrastructure.models import Problem
from app.modules.identity.infrastructure.models import User
from app.modules.learning.infrastructure.models import LearningPlan, LearningTask, LearningTaskAttempt
from app.modules.learning.infrastructure.pbl_mastery import evaluate_pbl_plan
from app.modules.pbl.application.records import InferenceRequest, InferenceResult
from app.modules.pbl.infrastructure.checked_gateway import CheckedGateway
from app.modules.pbl.infrastructure.models import PblDiagnosticSnapshot, PblParticipation, PblSession
from scripts.transition_pbl_t14 import _backup, transition


def _attempt(score=None, *, evidence=True, dimension_scores=None):
    return SimpleNamespace(
        score=score,
        evidence=["evidence"] if evidence else [],
        answer={"dimension_scores": dimension_scores or {}},
    )


def _task(
    task_id,
    task_type,
    target_type,
    target_code,
    *,
    cycle=1,
    status="completed",
    score=None,
    evidence=True,
    dimensions=None,
):
    return SimpleNamespace(
        id=task_id,
        task_type=task_type,
        target_type=target_type,
        target_code=target_code,
        cycle_number=cycle,
        status=status,
        public_definition={"target_dimension_ids": list((dimensions or {}).keys())},
        attempt=None
        if status in {"inactive", "skipped", "pending"}
        else _attempt(score, evidence=evidence, dimension_scores=dimensions),
    )


def _plan(tasks, *, cycle=1):
    return SimpleNamespace(
        id=20,
        student_id=3,
        source_type="pbl_suggestion",
        status="active",
        current_cycle=cycle,
        max_cycles=2,
        target_dimension_ids=["evidence_reasoning"],
        version=1,
        verification_status="not_ready",
        automation_exhausted=False,
        decision_basis={},
        decision_policy_version="",
        evaluated_at=None,
        completed_at=None,
        tasks=tasks,
    )


def _session():
    session = MagicMock()
    session.scalar.return_value = None
    return session


def test_first_cycle_requires_every_scored_target_and_evidence() -> None:
    plan = _plan(
        [
            _task(1, "discussion", "discussion", "discussion"),
            _task(2, "knowledge_review", "knowledge_gap", "point-a", score=0),
            _task(3, "retest", "knowledge_gap", "point-a", score=100),
            _task(4, "micro_drill", "reasoning_issue", "evidence_reasoning", score=70),
            _task(5, "discussion", "discussion", "discussion", cycle=2, status="inactive"),
            _task(6, "knowledge_review", "knowledge_gap", "point-a", cycle=2, status="inactive"),
            _task(7, "retest", "knowledge_gap", "point-a", cycle=2, status="inactive"),
            _task(8, "micro_drill", "reasoning_issue", "evidence_reasoning", cycle=2, status="inactive"),
        ]
    )
    assert evaluate_pbl_plan(_session(), plan)
    assert plan.status == "completed"
    assert plan.verification_status == "improved"
    assert plan.decision_basis["result"] == "improved"


def test_first_cycle_activates_only_failed_target_with_distinct_second_variant() -> None:
    tasks = [
        _task(1, "discussion", "discussion", "discussion"),
        _task(2, "retest", "knowledge_gap", "point-a", score=0),
        _task(3, "micro_drill", "reasoning_issue", "evidence_reasoning", score=80),
        _task(4, "discussion", "discussion", "discussion", cycle=2, status="inactive"),
        _task(5, "knowledge_review", "knowledge_gap", "point-a", cycle=2, status="inactive"),
        _task(6, "retest", "knowledge_gap", "point-a", cycle=2, status="inactive"),
        _task(7, "micro_drill", "reasoning_issue", "evidence_reasoning", cycle=2, status="inactive"),
    ]
    plan = _plan(tasks)
    assert evaluate_pbl_plan(_session(), plan)
    assert plan.current_cycle == 2 and plan.status == "active"
    assert [task.status for task in tasks[3:]] == ["pending", "pending", "pending", "skipped"]
    assert plan.decision_basis["failed_targets"] == [
        {"target_type": "knowledge_gap", "target_code": "point-a"}
    ]


def test_second_cycle_failure_is_exhausted_and_missing_case_dimension_fails_closed() -> None:
    tasks = [
        _task(1, "discussion", "discussion", "discussion", cycle=2),
        _task(
            2,
            "focused_retry",
            "case_retry",
            "case:9",
            cycle=2,
            score=95,
            dimensions={"evidence_reasoning": 69, "problem_representation": 95},
        ),
    ]
    plan = _plan(tasks, cycle=2)
    plan.target_dimension_ids = ["evidence_reasoning", "problem_representation"]
    assert evaluate_pbl_plan(_session(), plan)
    assert plan.verification_status == "needs_reinforcement"
    assert plan.automation_exhausted is True
    assert plan.decision_basis["offline_support_required"] is True
    assert any(
        check["target_code"] == "evidence_reasoning" and not check["passed"]
        for check in plan.decision_basis["checks"]
    )


def test_incomplete_cycle_and_repeated_evaluation_do_not_duplicate_decisions() -> None:
    plan = _plan([_task(1, "retest", "knowledge_gap", "point-a", status="pending")])
    session = _session()
    assert evaluate_pbl_plan(session, plan) is False
    plan.tasks[0].status = "completed"
    plan.tasks[0].attempt = _attempt(100)
    assert evaluate_pbl_plan(session, plan) is True
    version = plan.version
    assert evaluate_pbl_plan(session, plan) is False
    assert plan.version == version


def _phase_result(phase="problem_framing", decision="advance", evidence=("new",), status="probing"):
    return InferenceResult(
        assistant_reply="继续完成当前阶段。",
        diagnostic_status=status,
        follow_up_question="请补充依据。" if status == "probing" else None,
        phase_assessment={
            "phase": phase,
            "decision": decision,
            "evidence_message_ids": list(evidence),
            "evidence_summary": "当前阶段证据摘要。",
            "missing_elements": [],
        },
    )


def _request(phase="problem_framing"):
    return InferenceRequest(
        session_id=1,
        topic_code="pathology.inflammation",
        question="当前回答",
        history=(
            {"id": "old", "role": "student", "content": "旧证据", "request_revision": 1},
            {"id": "recent", "role": "student", "content": "新证据", "request_revision": 3},
        ),
        message_id="new",
        current_phase=phase,
        phase_started_revision=2,
        current_revision=4,
    )


def test_phase_gateway_rejects_old_evidence_mismatch_and_early_completion() -> None:
    for invalid in (
        _phase_result(evidence=("old",)),
        _phase_result(phase="hypothesis"),
        _phase_result(decision="complete", status="ready"),
    ):
        gateway = MagicMock()
        gateway.infer.return_value = invalid
        checked = CheckedGateway(gateway).infer(_request())
        assert checked.diagnostic_status == "unavailable"
        assert not checked.knowledge_gaps and not checked.reasoning_issues


def test_phase_gateway_accepts_current_stage_evidence_and_synthesis_completion() -> None:
    gateway = MagicMock()
    gateway.infer.return_value = _phase_result()
    assert CheckedGateway(gateway).infer(_request()).phase_assessment["decision"] == "advance"

    gateway.infer.return_value = InferenceResult(
        assistant_reply="形成结构化学习线索。",
        diagnostic_status="ready",
        knowledge_gaps=(
            {
                "id": "gap",
                "point_code": "pathology.inflammation.vascular",
                "summary": "机制解释不足",
                "confidence": "medium",
                "evidence_message_ids": ["new"],
                "evidence_summary": "当前综合回答暴露薄弱点。",
            },
        ),
        recommended_questions=(
            {
                "title": "证据讨论",
                "prompt": "比较证据。",
                "objective": "建立证据链。",
                "linked_findings": ["gap"],
            },
        ),
        phase_assessment={
            "phase": "synthesis",
            "decision": "complete",
            "evidence_message_ids": ["new"],
            "evidence_summary": "完成综合解释。",
            "missing_elements": [],
        },
    )
    result = CheckedGateway(gateway).infer(_request("synthesis"))
    assert result.diagnostic_status == "ready"


def test_transition_restarts_history_marks_legacy_and_reconciles_pending_plan(db) -> None:
    case = seed_showcase_case(db)
    teacher = db.scalar(select(User).where(User.external_id == "demo_teacher"))
    student = db.scalar(select(User).where(User.external_id == "demo_student"))
    classroom = db.scalar(select(ClassRoom).where(ClassRoom.code == "demo_class_1"))
    assert teacher and student and classroom and isinstance(case, Problem)
    pbl_session = PblSession(
        class_id=classroom.id,
        teacher_id=teacher.id,
        topic_code="pathology.cell-injury",
        case_id=case.id,
        provider="coze",
        status="closed",
        goal_point_codes=["pathology.cell-injury.reversible"],
    )
    db.add(pbl_session)
    db.flush()
    completed_part = PblParticipation(session_id=pbl_session.id, student_id=student.id, revision=2)
    restarted_student = User(
        external_id="t14-history-student", role="student", nickname="history", class_ids=[classroom.code]
    )
    db.add(restarted_student)
    db.flush()
    restarted_part = PblParticipation(session_id=pbl_session.id, student_id=restarted_student.id, revision=4)
    db.add_all([completed_part, restarted_part])
    db.flush()
    db.add(
        PblDiagnosticSnapshot(
            participation_id=completed_part.id,
            revision=2,
            status="ready",
            schema_version=2,
            assistant_reply="legacy ready",
            knowledge_gaps=[],
            reasoning_issues=[],
            provider_metadata={},
        )
    )
    pending = LearningPlan(
        student_id=student.id,
        source_type="pbl_suggestion",
        source_id=501,
        source_context={
            "teacher_id": teacher.id,
            "class_id": classroom.id,
            "session_id": pbl_session.id,
            "snapshot_id": 1,
            "suggestion_id": 501,
            "point_codes": ["pathology.cell-injury.reversible"],
            "dimension_ids": [],
        },
        status="completed",
        verification_status="pending_teacher",
        due_at=case.created_at,
    )
    pending.tasks.extend(
        [
            LearningTask(
                position=1,
                task_type="discussion",
                dimension_id="discussion",
                status="completed",
                public_definition={"prompt": "discussion"},
                private_rubric={},
                attempt=LearningTaskAttempt(
                    student_id=student.id,
                    status="assessed",
                    answer={"text": "evidence"},
                    evidence=["discussion evidence"],
                ),
            ),
            LearningTask(
                position=2,
                task_type="retest",
                dimension_id="knowledge",
                status="completed",
                public_definition={
                    "point_code": "pathology.cell-injury.reversible",
                    "card_code": "pathology.cell-injury.reversible.retest",
                    "prompt": "retest",
                    "options": ["a", "b"],
                },
                private_rubric={"correct_option": 0, "explanation": "e"},
                attempt=LearningTaskAttempt(
                    student_id=student.id,
                    status="assessed",
                    answer={"selected_option": 1},
                    score=0,
                    evidence=["objective evidence"],
                ),
            ),
        ]
    )
    legacy = LearningPlan(
        student_id=restarted_student.id,
        source_type="pbl_suggestion",
        source_id=502,
        source_context={},
        status="completed",
        verification_status="improved",
        due_at=case.created_at,
    )
    db.add_all([pending, legacy])
    db.flush()

    result = transition(db)
    db.flush()
    assert result == {
        "participations_completed": 1,
        "participations_restarted": 1,
        "legacy_results_marked": 1,
        "pending_reconciled": 1,
        "failed_plan_ids": [],
    }
    assert completed_part.current_phase == "synthesis" and completed_part.phase_status == "completed"
    assert restarted_part.current_phase == "problem_framing"
    assert legacy.decision_basis["decision_source"] == "legacy_teacher"
    assert pending.current_cycle == 2 and pending.verification_status == "not_ready"
    second_cycle = [task for task in pending.tasks if task.cycle_number == 2]
    assert {task.variant_code for task in second_cycle if task.target_type == "knowledge_gap"} == {
        "pathology.cell-injury.reversible.practice.v2",
        "pathology.cell-injury.reversible.retest.v2",
    }
    assert all(task.status == "pending" for task in second_cycle)


def test_transition_backup_is_consistent_and_never_overwrites(db) -> None:
    source = Path(str(db.get_bind().url.database)).resolve()
    target = source.with_name("t14-backup.db")
    _backup(source, target)
    with closing(sqlite3.connect(target)) as backup:
        assert backup.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert backup.execute("SELECT name FROM sqlite_master WHERE name = 'pbl_participations'").fetchone() == (
            "pbl_participations",
        )
    try:
        _backup(source, target)
    except ValueError as error:
        assert str(error) == "Backup target already exists"
    else:
        raise AssertionError("Existing backup target must not be overwritten")


def test_transition_cli_is_dry_run_by_default_and_guards_apply(db) -> None:
    source = Path(str(db.get_bind().url.database)).resolve()
    working = source.with_name("t14-working.db")
    backup = source.with_name("t14-before-apply.db")
    script = Path(__file__).resolve().parents[1] / "scripts" / "transition_pbl_t14.py"
    _backup(source, working)

    dry_run = subprocess.run(
        [sys.executable, str(script), "--database", str(working)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert dry_run.returncode == 0, dry_run.stderr
    assert json.loads(dry_run.stdout)["mode"] == "dry-run"

    denied = subprocess.run(
        [sys.executable, str(script), "--database", str(working), "--apply", "--backup", str(backup)],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert denied.returncode == 2
    assert not backup.exists()

    applied = subprocess.run(
        [
            sys.executable,
            str(script),
            "--database",
            str(working),
            "--apply",
            "--confirm-development",
            "--backup",
            str(backup),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert applied.returncode == 0, applied.stderr
    assert json.loads(applied.stdout)["mode"] == "apply"
    with closing(sqlite3.connect(backup)) as backup_db:
        assert backup_db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
