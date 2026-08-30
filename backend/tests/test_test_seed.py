from app.db import Base, SessionLocal, engine
from app.models import CaseAssessment, CaseAttempt, LearningPlan, LearningTask, Problem, Report
from app.services.test_seed import seed_test_data


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_test_seed_is_idempotent_and_builds_each_demo_path() -> None:
    db = SessionLocal()
    try:
        first = seed_test_data(db)
        second = seed_test_data(db)
        assert first == second
        assert first["users"] == 4
        assert first["class_members"] == 2
        assert first["problems"] == 5
        assert first["pending_cases"] == 1
        assert first["conversations"] == 1
        assert first["reports"] == 1
        assert first["question_threads"] == 1
        assert first["case_attempts"] == 1
        assert db.query(CaseAssessment).count() == 1
        assert db.query(LearningPlan).count() == 1
        assert db.query(LearningTask).count() == 3
        assert db.query(Report).filter(Report.status == "pending_review").count() == 1
        assert db.query(Problem).filter(Problem.medical_review_status == "pending").count() == 1
        assert db.query(CaseAttempt).filter(CaseAttempt.status == "assessed").count() == 1
    finally:
        db.close()
