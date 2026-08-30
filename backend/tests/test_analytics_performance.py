from datetime import UTC, datetime, timedelta
from time import perf_counter

from sqlalchemy import event, insert

from app.db import Base, SessionLocal, engine
from app.models import CaseAssessment, CaseAttempt, ClassMember, ClassRoom, Problem, User
from app.services.analytics import case_detail, overview, student_detail


def test_analytics_matrix_scales_to_ten_thousand_attempts() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    now = datetime.now(UTC)
    dimensions = [
        {"dimension_id": dimension_id, "score": 70, "weighted_score": weight}
        for dimension_id, _label, weight, _stages in (
            ("information_gathering", "信息采集", 20, ("history",)),
            ("problem_representation", "问题表征", 15, ("problem_representation",)),
            ("differential_diagnosis", "鉴别诊断", 20, ("differential",)),
            ("evidence_reasoning", "证据推理", 15, ("differential",)),
            ("test_selection", "检查合理性", 15, ("tests",)),
            ("management_safety", "处置与安全意识", 15, ("management",)),
        )
    ]
    with SessionLocal() as db:
        db.execute(
            insert(User),
            [
                {
                    "id": 1,
                    "external_id": "perf-teacher",
                    "role": "teacher",
                    "nickname": "性能教师",
                    "avatar_url": "",
                    "class_ids": [],
                    "permissions": [],
                },
                *[
                    {
                        "id": student_id,
                        "external_id": f"perf-student-{student_id}",
                        "role": "student",
                        "nickname": f"学生{student_id}",
                        "avatar_url": "",
                        "class_ids": [],
                        "permissions": [],
                    }
                    for student_id in range(2, 102)
                ],
            ],
        )
        db.execute(
            insert(ClassRoom),
            {"id": 1, "name": "性能班", "code": "perf-class", "teacher_id": 1, "status": "active"},
        )
        db.execute(
            insert(ClassMember),
            [{"class_id": 1, "student_id": student_id} for student_id in range(2, 102)],
        )
        db.execute(
            insert(Problem),
            [
                {
                    "id": problem_id,
                    "type": "病例分析",
                    "title": f"性能病例{problem_id}",
                    "description": "performance",
                    "target": "all",
                    "target_label": "全体学生",
                    "target_ids": "",
                    "status": "published",
                    "slug": f"perf-case-{problem_id}",
                    "content_type": "guided_case",
                    "specialty": "教学",
                    "difficulty": "basic",
                    "estimated_minutes": 10,
                    "version": 1,
                    "author_id": 1,
                    "medical_review_status": "approved",
                    "capability_tags": [],
                }
                for problem_id in range(1, 11)
            ],
        )
        attempts = []
        assessments = []
        for attempt_id in range(1, 10001):
            student_id = 2 + ((attempt_id - 1) % 100)
            problem_id = 1 + ((attempt_id - 1) % 10)
            started_at = now - timedelta(minutes=attempt_id % 240)
            attempts.append(
                {
                    "id": attempt_id,
                    "problem_id": problem_id,
                    "student_id": student_id,
                    "problem_version": 1,
                    "status": "assessed",
                    "current_stage": "completed",
                    "started_at": started_at,
                    "completed_at": started_at + timedelta(minutes=20),
                    "assessed_at": started_at + timedelta(minutes=20),
                }
            )
            assessments.append(
                {
                    "id": attempt_id,
                    "attempt_id": attempt_id,
                    "total_score": 70 + attempt_id % 20,
                    "dimensions": dimensions,
                    "strengths": [],
                    "weaknesses": [],
                    "next_steps": [],
                    "summary": "performance",
                    "focus_stage": "history",
                    "model_name": "deterministic-fallback",
                    "prompt_version": "case-v2",
                    "fallback_used": True,
                    "latency_ms": 0,
                }
            )
        db.execute(insert(CaseAttempt), attempts)
        db.execute(insert(CaseAssessment), assessments)
        db.commit()
        teacher = db.get(User, 1)
        student = db.get(User, 2)
        assert teacher is not None and student is not None

        overview(teacher, 1, None, None, db)
        case_detail(teacher, 1, 1, None, None, db)
        student_detail(teacher, 2, 1, None, None, db)
        statements = 0

        def count_statements(*_args) -> None:
            nonlocal statements
            statements += 1

        event.listen(engine, "before_cursor_execute", count_statements)
        try:
            started = perf_counter()
            result = overview(teacher, 1, None, None, db)
            case_detail(teacher, 1, 1, None, None, db)
            student_detail(teacher, 2, 1, None, None, db)
            elapsed = perf_counter() - started
        finally:
            event.remove(engine, "before_cursor_execute", count_statements)
        assert result["student_count"] == 100
        assert result["eligible_pairs"] == 1000
        assert statements < 30
        assert elapsed < 2
