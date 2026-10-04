"""Retired HTTP flows preserve history and cannot create new learning evidence."""

from datetime import UTC, datetime

from sqlalchemy import func, select

from app.modules.content.infrastructure.models import KnowledgeCardContribution, Problem
from app.modules.identity.infrastructure.models import User
from app.modules.learning.infrastructure.evidence_models import LearningEvidenceEvent
from app.modules.learning.infrastructure.models import ReviewAttempt, ReviewItem, ReviewState
from app.modules.qa.infrastructure.models import QuestionThread
from tests.test_pbl_api import _headers, _login

POINT = "pathology.cell-injury.reversible"


def _case_payload(client, headers, slug):
    response = client.post(
        "/problems/case-drafts/generate",
        headers=headers,
        json={"topic": "肺炎", "learner_level": "本科生", "learning_objectives": ["结构化推理"]},
    )
    assert response.status_code == 200
    draft = response.json()
    return {
        "type": "病例分析",
        "title": draft["title"],
        "description": draft["description"],
        "content_type": "guided_case",
        "slug": slug,
        "case_definition": draft["case_definition"],
        "rubric": draft["rubric"],
    }


def _count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_retired_discussion_reads_and_writes_keep_history_and_cannot_change_type(client, db):
    owner = _headers(_login(client, "teacher", "t63-owner"))
    other = _headers(_login(client, "teacher", "t63-other"))
    student = _headers(_login(client, "student", "t63-student"))
    owner_id = db.scalar(select(User.id).where(User.external_id == "t63-owner"))
    student_id = db.scalar(select(User.id).where(User.external_id == "t63-student"))
    historical = Problem(
        type="讨论题", title="historical", content_type="question", author_id=owner_id, status="published"
    )
    active = Problem(type="病例分析", title="active", content_type="guided_case", author_id=owner_id)
    db.add_all([historical, active])
    db.flush()
    thread = QuestionThread(problem_id=historical.id, student_id=student_id)
    db.add(thread)
    db.commit()
    payload = _case_payload(client, owner, "t63-case")
    question_payload = {"type": "讨论题", "title": "new", "content_type": "question"}
    for headers in [owner, student]:
        items = client.get("/problems", headers=headers).json()
        assert all(item["content_type"] == "guided_case" for item in items)
        assert client.get(f"/problems/{historical.id}", headers=headers).status_code == 404
    assert client.get("/student/questions", headers=student).json() == []
    assert client.get(f"/student/questions/{historical.id}", headers=student).status_code == 404
    assert client.get(f"/problems/{historical.id}/thread", headers=student).status_code == 404
    for method, path, headers, body in [
        ("post", "/problems", owner, question_payload),
        ("put", f"/problems/{historical.id}", owner, payload),
        ("put", f"/problems/{active.id}", owner, question_payload),
        ("post", f"/problems/{historical.id}/publish", owner, None),
        ("post", f"/problems/{historical.id}/reject", owner, None),
        ("post", f"/problems/{historical.id}/thread", student, {"messages": []}),
    ]:
        response = getattr(client, method)(path, headers=headers, json=body)
        assert response.status_code == 409, response.text
        assert response.json()["detail"]["code"] == "RETIRED_FLOW"
    assert client.put(f"/problems/{historical.id}", headers=other, json=payload).status_code == 404
    assert client.post("/problems", headers=student, json=payload).status_code == 403
    assert client.post("/problems", json=payload).status_code == 401
    db.expire_all()
    assert db.get(Problem, historical.id).content_type == "question"
    assert db.get(Problem, active.id).content_type == "guided_case"
    assert _count(db, Problem) == 2
    assert _count(db, QuestionThread) == 1
    assert db.get(QuestionThread, thread.id) is not None


def test_retired_teacher_cards_preserve_rows_and_permission_boundaries(client, db):
    owner = _headers(_login(client, "teacher", "t63-card-owner"))
    reviewer = _headers(_login(client, "teacher", "demo_reviewer"))
    student = _headers(_login(client, "student", "t63-card-student"))
    owner_id = db.scalar(select(User.id).where(User.external_id == "t63-card-owner"))
    card = KnowledgeCardContribution(
        owner_id=owner_id,
        point_code=POINT,
        card_type="recall",
        prompt="historical",
        explanation="private",
        status="pending",
    )
    db.add(card)
    db.commit()
    payload = {"point_code": POINT, "card_type": "recall", "prompt": "new", "explanation": "new"}
    for headers in [owner, student]:
        assert client.get("/knowledge/cards", headers=headers).json() == []
    assert client.get("/knowledge/review-queue", headers=reviewer).json() == []
    for method, path, headers, body in [
        ("post", "/knowledge/teacher/cards", owner, payload),
        ("put", f"/knowledge/teacher/cards/{card.id}", owner, payload),
        ("post", f"/knowledge/teacher/cards/{card.id}/submit", owner, None),
        ("post", f"/knowledge/teacher/cards/{card.id}/review", reviewer, {"decision": "approved"}),
        ("post", f"/knowledge/teacher/cards/{card.id}/disable", reviewer, None),
    ]:
        response = getattr(client, method)(path, headers=headers, json=body)
        assert response.status_code == 409, response.text
        assert response.json()["detail"]["code"] == "RETIRED_FLOW"
        assert getattr(client, method)(path, json=body).status_code == 401
        assert getattr(client, method)(path, headers=student, json=body).status_code == 403
    assert client.post(f"/knowledge/teacher/cards/{card.id}/disable", headers=owner).status_code == 403
    db.refresh(card)
    assert card.status == "pending" and card.prompt == "historical" and card.explanation == "private"
    assert _count(db, KnowledgeCardContribution) == 1


def test_retired_review_api_is_empty_without_new_attempts_or_evidence_and_map_remains(client, db):
    student = _headers(_login(client, "student", "t63-review-student"))
    teacher = _headers(_login(client, "teacher", "t63-review-teacher"))
    student_id = db.scalar(select(User.id).where(User.external_id == "t63-review-student"))
    historical = ReviewItem(
        student_id=student_id, point_code=POINT, source_type="assistant_message", source_id="historic", active=True
    )
    state = ReviewState(
        student_id=student_id, point_code=POINT, card_code="historical:card", due_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    db.add_all([historical, state])
    db.commit()
    models = [ReviewItem, ReviewState, ReviewAttempt, LearningEvidenceEvent]
    before = [_count(db, model) for model in models]
    for path in ["/learning/review-dashboard", "/learning/review-items"]:
        assert client.get(path, headers=student).json() == {"due_count": 0, "weak_point_codes": [], "items": []}
        assert client.get(path, headers=teacher).status_code == 403
        assert client.get(path).status_code == 401
    assert client.get("/learning/reviews/due", headers=student).json() == []
    writes = [
        ("/learning/exit-quiz", {"topic_codes": [POINT]}),
        ("/learning/reviews/historical:card/grade", {"selected_option": 0, "confidence": "high"}),
        ("/learning/recall-cards/1/reveal", None),
        ("/learning/recall-cards/1/rate", {"rating": "good"}),
        ("/learning/review-items", {"point_code": POINT, "source_type": "message", "source_id": "new"}),
        (f"/learning/review-items/{historical.id}/dismiss", None),
    ]
    for path, payload in writes:
        response = client.post(path, headers=student, json=payload)
        assert response.status_code == 409, response.text
        assert response.json()["detail"]["code"] == "RETIRED_FLOW"
        assert client.post(path, headers=teacher, json=payload).status_code == 403
        assert client.post(path, json=payload).status_code == 401
    db.expire_all()
    assert [_count(db, model) for model in models] == before
    assert db.get(ReviewItem, historical.id).active is True
    response = client.get("/learning/knowledge-map", headers=student)
    assert response.status_code == 200
    assert len(response.json()["items"]) == 30
    assert {item["code"]: item["status"] for item in response.json()["items"]}[POINT] == "weak"
