import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select

from app.modules.classroom.infrastructure.models import ClassRoom
from app.modules.identity.infrastructure.models import User
from app.modules.learning.infrastructure.models import (
    LearningPlan,
    LearningPlanEvaluation,
    LearningTask,
    LearningTaskAttempt,
)
from app.modules.learning.infrastructure.pbl_mastery import evaluate_pbl_plan
from app.modules.pbl.infrastructure.models import PblDiagnosticSnapshot, PblParticipation, PblSession
from scripts.backfill_pbl_evaluations import backfill
from scripts.transition_pbl_t14 import _backup


def _login(client, external_id: str) -> tuple[dict[str, str], int]:
    response = client.post(
        "/auth/demo-login",
        json={"role": "student", "external_id": external_id, "nickname": external_id, "avatar_url": ""},
    )
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["access_token"]}, response.json()["user"]["id"]


def _base(db, client):
    student_headers, student_id = _login(client, "t15-student")
    outsider_headers, _ = _login(client, "t15-outsider")
    teacher = User(external_id="t15-teacher", role="teacher", nickname="teacher", class_ids=[])
    db.add(teacher)
    db.flush()
    classroom = ClassRoom(name="T15", code="t15", teacher_id=teacher.id)
    db.add(classroom)
    db.flush()
    session = PblSession(
        class_id=classroom.id,
        teacher_id=teacher.id,
        topic_code="pathology.inflammation",
        provider="coze",
        status="active",
        case_context={"title": "急性炎症血管反应"},
        goal_point_codes=["pathology.inflammation.vascular"],
    )
    db.add(session)
    db.flush()
    return student_headers, outsider_headers, student_id, session, teacher, classroom


def test_student_report_is_progressive_private_and_combines_classroom_assignments(client, db) -> None:
    student_headers, outsider_headers, student_id, session, _, _ = _base(db, client)
    student_part = PblParticipation(
        session_id=session.id,
        student_id=student_id,
        revision=4,
        current_phase="completed",
        phase_status="completed",
        phase_completed_at=datetime.now(UTC),
    )
    other = User(external_id="t15-source-student", role="student", nickname="source", class_ids=[])
    db.add_all([student_part, other])
    db.flush()
    personal = PblDiagnosticSnapshot(
        participation_id=student_part.id,
        revision=4,
        status="ready",
        schema_version=3,
        phase="synthesis",
        phase_decision="complete",
        phase_evidence_summary="能够整合血流与通透性证据。",
        assistant_reply="形成学习线索。",
        knowledge_gaps=[
            {
                "id": "gap-personal",
                "point_code": "pathology.inflammation.vascular",
                "summary": "血管反应机制仍不完整",
                "confidence": "high",
                "evidence_summary": "未区分血流增加与渗出。",
            }
        ],
        reasoning_issues=[],
        provider_metadata={},
    )
    other_part = PblParticipation(session_id=session.id, student_id=other.id, revision=4)
    db.add_all([personal, other_part])
    db.flush()
    other_snapshot = PblDiagnosticSnapshot(
        participation_id=other_part.id,
        revision=4,
        status="ready",
        schema_version=3,
        phase="synthesis",
        phase_decision="complete",
        phase_evidence_summary="other secret evidence",
        assistant_reply="other secret reply",
        knowledge_gaps=[
            {
                "id": "other-secret",
                "point_code": "pathology.inflammation.cellular",
                "summary": "other secret diagnosis",
                "confidence": "high",
                "evidence_summary": "other secret evidence",
            }
        ],
        reasoning_issues=[],
        provider_metadata={"secret": "provider"},
    )
    db.add(other_snapshot)
    db.flush()
    due = datetime.now(UTC) + timedelta(days=7)
    personal_plan = LearningPlan(
        student_id=student_id,
        source_type="pbl_suggestion",
        source_id=1001,
        source_context={"session_id": session.id, "snapshot_id": personal.id},
        status="active",
        current_cycle=2,
        due_at=due,
    )
    classroom_plan = LearningPlan(
        student_id=student_id,
        source_type="pbl_suggestion",
        source_id=1002,
        source_context={"session_id": session.id, "snapshot_id": other_snapshot.id},
        status="completed",
        verification_status="improved",
        due_at=due,
    )
    db.add_all([personal_plan, classroom_plan])
    db.flush()
    personal_plan.evaluations.append(
        LearningPlanEvaluation(
            cycle_number=1,
            policy_version="pbl-mastery-v1",
            result="next_cycle_activated",
            checks=[
                {
                    "target_type": "knowledge_gap",
                    "target_code": "pathology.inflammation.vascular",
                    "threshold": 100,
                    "score": 0,
                    "evidence_present": True,
                    "passed": False,
                }
            ],
            failed_targets=[
                {"target_type": "knowledge_gap", "target_code": "pathology.inflammation.vascular"}
            ],
            automation_exhausted=False,
            record_source="runtime",
            evaluated_at=datetime.now(UTC),
        )
    )
    personal_plan.tasks.append(
        LearningTask(
            position=1,
            cycle_number=2,
            target_type="knowledge_gap",
            target_code="pathology.inflammation.vascular",
            variant_code="vascular.retest.v2",
            task_type="retest",
            dimension_id="knowledge",
            status="pending",
            public_definition={"prompt": "第二轮再测"},
            private_rubric={"correct_option": 1, "secret": "rubric-secret"},
        )
    )
    db.commit()

    page = client.get("/student/pbl-learning-reports", headers=student_headers)
    assert page.status_code == 200, page.text
    assert page.json()["summary"]["status_counts"]["learning_cycle_2"] == 1
    assert page.json()["summary"]["completed_personal_discussions"] == 1
    assert page.json()["summary"]["recurring_targets"][0]["occurrences"] == 1
    detail = client.get(f"/student/pbl-learning-reports/{session.id}", headers=student_headers)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["status"] == "learning_cycle_2"
    assert body["diagnosis"]["knowledge_gaps"][0]["summary"] == "血管反应机制仍不完整"
    assert {plan["assignment_basis"] for plan in body["plans"]} == {"personal", "classroom"}
    serialized = detail.text
    assert "other secret" not in serialized
    assert "rubric-secret" not in serialized
    assert "private_rubric" not in serialized and '"answer"' not in serialized
    assert client.get(f"/student/pbl-learning-reports/{session.id}", headers=outsider_headers).status_code == 404


def test_report_counts_each_v4_completed_personal_target_once_and_excludes_invalid_ready_snapshot(client, db) -> None:
    student_headers, _, student_id, session, _, _ = _base(db, client)
    participation = PblParticipation(
        session_id=session.id,
        student_id=student_id,
        revision=6,
        current_phase="completed",
        phase_status="completed",
        phase_completed_at=datetime.now(UTC),
        interaction_style="direct",
    )
    db.add(participation)
    db.flush()
    db.add_all(
        [
            PblDiagnosticSnapshot(
                participation_id=participation.id,
                revision=4,
                status="ready",
                schema_version=4,
                phase="synthesis",
                phase_decision="complete",
                phase_evidence_summary="整合机制和证据。",
                assistant_reply="形成统一研讨学习线索。",
                knowledge_gaps=[
                    {
                        "id": "v4-gap-1",
                        "point_code": "pathology.inflammation.vascular",
                        "summary": "血管反应需要巩固",
                        "confidence": "high",
                        "evidence_summary": "未区分渗出与充血。",
                    },
                    {
                        "id": "v4-gap-duplicate",
                        "point_code": "pathology.inflammation.vascular",
                        "summary": "同一目标不重复计数",
                        "confidence": "medium",
                        "evidence_summary": "同一讨论中的补充说明。",
                    },
                ],
                reasoning_issues=[
                    {
                        "id": "v4-reasoning",
                        "dimension_id": "evidence_reasoning",
                        "summary": "证据链仍不完整",
                        "issue_type": "missing_evidence",
                        "improvement": "补充反对证据。",
                        "evidence_summary": "没有说明反证。",
                    }
                ],
                provider_metadata={},
            ),
            PblDiagnosticSnapshot(
                participation_id=participation.id,
                revision=6,
                status="ready",
                schema_version=4,
                phase="evidence",
                phase_decision="advance",
                phase_evidence_summary="不是合法完成快照。",
                assistant_reply="继续讨论。",
                knowledge_gaps=[],
                reasoning_issues=[],
                provider_metadata={},
            ),
        ]
    )
    db.commit()

    page = client.get("/student/pbl-learning-reports", headers=student_headers)
    assert page.status_code == 200, page.text
    summary = page.json()["summary"]
    assert summary["completed_personal_discussions"] == 1
    assert {
        (item["target_type"], item["target_code"], item["occurrences"])
        for item in summary["recurring_targets"]
    } == {
        ("knowledge_gap", "pathology.inflammation.vascular", 1),
        ("reasoning_issue", "evidence_reasoning", 1),
    }
    detail = client.get(f"/student/pbl-learning-reports/{session.id}", headers=student_headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["diagnosis"]["created_at"] is not None
    assert len(detail.json()["diagnosis"]["knowledge_gaps"]) == 2


def test_discussing_participation_is_exposed_as_a_progressive_report(client, db) -> None:
    student_headers, _, student_id, session, _, _ = _base(db, client)
    participation = PblParticipation(
        session_id=session.id,
        student_id=student_id,
        revision=2,
        current_phase="hypothesis",
        phase_status="active",
        phase_started_revision=2,
    )
    db.add(participation)
    db.flush()
    db.add(
        PblDiagnosticSnapshot(
            participation_id=participation.id,
            revision=2,
            status="probing",
            schema_version=3,
            phase="hypothesis",
            phase_decision="continue",
            phase_evidence_summary="已提出机制假设。",
            phase_missing_elements=["说明仍不确定的部分"],
            assistant_reply="继续澄清假设。",
            knowledge_gaps=[],
            reasoning_issues=[],
            provider_metadata={},
        )
    )
    db.commit()

    response = client.get(f"/student/pbl-learning-reports/{session.id}", headers=student_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "discussing"
    assert body["next_action"]["kind"] == "discussion"
    phase = body["phase_progress"][1]
    assert {key: value for key, value in phase.items() if key != "evidenced_at"} == {
        "phase": "hypothesis",
        "label": "提出假设",
        "state": "current",
        "evidence_summary": "已提出机制假设。",
        "missing_elements": ["说明仍不确定的部分"],
    }
    assert phase["evidenced_at"] is not None


def test_plan_evaluation_history_is_transactional_and_idempotent(client, db) -> None:
    _, _, student_id, session, _, _ = _base(db, client)
    plan = LearningPlan(
        student_id=student_id,
        source_type="pbl_suggestion",
        source_id=2001,
        source_context={"session_id": session.id, "snapshot_id": 0},
        status="active",
        due_at=datetime.now(UTC) + timedelta(days=7),
    )
    plan.tasks.append(
        LearningTask(
            position=1,
            cycle_number=1,
            target_type="knowledge_gap",
            target_code="pathology.inflammation.vascular",
            variant_code="vascular.retest.v1",
            task_type="retest",
            dimension_id="knowledge",
            status="completed",
            public_definition={"prompt": "再测"},
            private_rubric={"correct_option": 0},
            attempt=LearningTaskAttempt(
                student_id=student_id,
                status="assessed",
                answer={"selected_option": 0},
                score=100,
                evidence=["客观作答：正确"],
                assessed_at=datetime.now(UTC),
            ),
        )
    )
    db.add(plan)
    db.flush()
    assert evaluate_pbl_plan(db, plan)
    db.flush()
    evaluation_count = db.scalar(
        select(func.count(LearningPlanEvaluation.id)).where(LearningPlanEvaluation.plan_id == plan.id)
    )
    assert evaluation_count == 1
    assert not evaluate_pbl_plan(db, plan)
    db.flush()
    evaluation = db.scalar(select(LearningPlanEvaluation).where(LearningPlanEvaluation.plan_id == plan.id))
    assert evaluation and evaluation.result == "improved" and evaluation.checks[0]["score"] == 100


def test_second_cycle_appends_to_instead_of_overwriting_first_cycle_evaluation(client, db) -> None:
    _, _, student_id, session, _, _ = _base(db, client)
    now = datetime.now(UTC)
    plan = LearningPlan(
        student_id=student_id,
        source_type="pbl_suggestion",
        source_id=2002,
        source_context={"session_id": session.id, "snapshot_id": 0},
        status="active",
        due_at=now + timedelta(days=7),
    )
    for position, cycle, score, status, variant in [
        (1, 1, 0, "completed", "vascular.retest.v1"),
        (2, 2, 100, "inactive", "vascular.retest.v2"),
    ]:
        plan.tasks.append(
            LearningTask(
                position=position,
                cycle_number=cycle,
                target_type="knowledge_gap",
                target_code="pathology.inflammation.vascular",
                variant_code=variant,
                task_type="retest",
                dimension_id="knowledge",
                status=status,
                public_definition={"prompt": f"第 {cycle} 轮再测"},
                private_rubric={},
                attempt=LearningTaskAttempt(
                    student_id=student_id,
                    status="assessed",
                    answer={},
                    score=score,
                    evidence=["客观作答：已评估"],
                    assessed_at=now,
                ),
            )
        )
    db.add(plan)
    db.flush()

    assert evaluate_pbl_plan(db, plan)
    assert plan.current_cycle == 2
    assert plan.tasks[1].status == "pending"
    plan.tasks[1].status = "completed"
    assert evaluate_pbl_plan(db, plan)
    db.flush()

    history = db.scalars(
        select(LearningPlanEvaluation)
        .where(LearningPlanEvaluation.plan_id == plan.id)
        .order_by(LearningPlanEvaluation.cycle_number)
    ).all()
    assert [(item.cycle_number, item.result) for item in history] == [
        (1, "next_cycle_activated"),
        (2, "improved"),
    ]
    assert [item.checks[0]["score"] for item in history] == [0, 100]


def test_classroom_task_creates_a_report_without_exposing_the_source_students_diagnosis(client, db) -> None:
    student_headers, _, student_id, session, _, _ = _base(db, client)
    source_student = User(external_id="t15-class-source", role="student", nickname="source", class_ids=[])
    db.add(source_student)
    db.flush()
    source_participation = PblParticipation(session_id=session.id, student_id=source_student.id, revision=4)
    db.add(source_participation)
    db.flush()
    source_snapshot = PblDiagnosticSnapshot(
        participation_id=source_participation.id,
        revision=4,
        status="ready",
        schema_version=3,
        phase="synthesis",
        phase_decision="complete",
        phase_evidence_summary="source-private-phase-evidence",
        assistant_reply="source-private-reply",
        knowledge_gaps=[
            {
                "id": "source-private-gap",
                "point_code": "pathology.inflammation.vascular",
                "summary": "source-private-summary",
                "confidence": "high",
                "evidence_summary": "source-private-evidence",
            }
        ],
        reasoning_issues=[],
        provider_metadata={},
    )
    db.add(source_snapshot)
    db.flush()
    db.add(
        LearningPlan(
            student_id=student_id,
            source_type="pbl_suggestion",
            source_id=2501,
            source_context={"session_id": session.id, "snapshot_id": source_snapshot.id},
            status="active",
            due_at=datetime.now(UTC) + timedelta(days=7),
        )
    )
    db.commit()

    response = client.get(f"/student/pbl-learning-reports/{session.id}", headers=student_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "learning_cycle_1"
    assert body["phase_progress"] == []
    assert body["diagnosis"] == {"created_at": None, "knowledge_gaps": [], "reasoning_issues": []}
    assert body["plans"][0]["assignment_basis"] == "classroom"
    assert "source-private" not in response.text


def test_backfill_reconstructs_only_provable_cycles_and_marks_teacher_history_legacy(client, db) -> None:
    _, _, student_id, session, _, _ = _base(db, client)
    assessed_at = datetime.now(UTC)
    automatic = LearningPlan(
        student_id=student_id,
        source_type="pbl_suggestion",
        source_id=3001,
        source_context={"session_id": session.id, "snapshot_id": 0},
        status="completed",
        verification_status="improved",
        current_cycle=1,
        decision_basis={"decision_source": "automatic", "policy_version": "pbl-mastery-v1", "cycle": 1},
        evaluated_at=assessed_at,
        completed_at=assessed_at,
        due_at=assessed_at + timedelta(days=7),
    )
    automatic.tasks.append(
        LearningTask(
            position=1,
            cycle_number=1,
            target_type="knowledge_gap",
            target_code="pathology.inflammation.vascular",
            variant_code="vascular.retest.v1",
            task_type="retest",
            dimension_id="knowledge",
            status="completed",
            public_definition={"prompt": "再测"},
            private_rubric={},
            attempt=LearningTaskAttempt(
                student_id=student_id,
                status="assessed",
                answer={},
                score=100,
                evidence=["客观作答：正确"],
                assessed_at=assessed_at,
            ),
        )
    )
    legacy = LearningPlan(
        student_id=student_id,
        source_type="pbl_suggestion",
        source_id=3002,
        source_context={"session_id": session.id, "snapshot_id": 0},
        status="completed",
        verification_status="needs_reinforcement",
        current_cycle=1,
        decision_basis={"decision_source": "legacy_teacher"},
        due_at=assessed_at + timedelta(days=7),
    )
    db.add_all([automatic, legacy])
    db.flush()

    result = backfill(db)
    assert result == {"runtime_existing": 0, "automatic_created": 1, "legacy_created": 1}
    db.flush()
    evaluations = db.scalars(
        select(LearningPlanEvaluation)
        .where(LearningPlanEvaluation.plan_id.in_([automatic.id, legacy.id]))
        .order_by(LearningPlanEvaluation.plan_id)
    ).all()
    assert [(item.record_source, item.result) for item in evaluations] == [
        ("backfill", "improved"),
        ("legacy", "needs_reinforcement"),
    ]
    assert evaluations[0].checks[0]["score"] == 100
    assert evaluations[1].checks == []


def test_backfill_cli_is_dry_run_by_default_and_requires_a_new_backup_for_apply(db) -> None:
    source = Path(str(db.get_bind().url.database)).resolve()
    working = source.with_name("t15-backfill-working.db")
    backup = source.with_name("t15-backfill-before-apply.db")
    script = Path(__file__).resolve().parents[1] / "scripts" / "backfill_pbl_evaluations.py"
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
    assert backup.is_file()

    existing_backup = subprocess.run(
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
    assert existing_backup.returncode != 0
    assert "Backup target already exists" in existing_backup.stderr
