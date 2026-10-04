from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from app.bootstrap.seed import seed_showcase_case
from app.modules.content.domain.card_blueprints import CARDS
from app.modules.content.infrastructure.knowledge_catalog_repository import SqlAlchemyKnowledgeCatalogRepository
from app.modules.identity.infrastructure.models import User
from app.modules.learning.application.knowledge_review import KnowledgeReviewApplication
from app.modules.learning.infrastructure.knowledge_review_repository import SqlAlchemyReviewRepository
from app.modules.learning.infrastructure.models import ReviewItem, ReviewState
from app.shared.actor import Actor

NOW = datetime(2026, 8, 31, tzinfo=UTC)


def _catalog(db) -> SqlAlchemyKnowledgeCatalogRepository:
    seed_showcase_case(db)
    return SqlAlchemyKnowledgeCatalogRepository(db)


def test_versioned_pathology_catalog_has_five_topics_and_thirty_points(db) -> None:
    points = _catalog(db).tree_view()
    assert len(points) == 30 and len(CARDS) == 120
    assert {point["system_code"] for point in points} == {
        "pathology.cell-injury",
        "pathology.inflammation",
        "pathology.repair",
        "pathology.circulatory",
        "pathology.neoplasm",
    }
    assert all(
        sum(point["system_code"] == system for point in points) == 6
        for system in {point["system_code"] for point in points}
    )
    assert {card.point_code for card in CARDS} == {point["code"] for point in points}


def _student_token(client) -> str:
    response = client.post(
        "/auth/demo-login",
        json={"role": "student", "external_id": "t08-student", "nickname": "学生", "avatar_url": ""},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _teacher_token(client, external_id: str) -> str:
    response = client.post(
        "/auth/demo-login",
        json={"role": "teacher", "external_id": external_id, "nickname": "教师", "avatar_url": ""},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_knowledge_map_reads_persisted_student_history_not_catalog_browsing(client, db) -> None:
    _student_token(client)
    student = db.scalar(select(User).where(User.external_id == "t08-student"))
    assert student is not None
    catalog = _catalog(db)
    service = KnowledgeReviewApplication(SqlAlchemyReviewRepository(db), catalog)
    actor = Actor.from_user(student)
    initial = {item.code: item.status for item in service.knowledge_map(actor)}
    assert initial["pathology.cell-injury.reversible"] == "not_started"

    db.add(
        ReviewItem(
            student_id=student.id,
            point_code="pathology.cell-injury.reversible",
            source_type="assistant_message",
            source_id="historical-message-1",
            active=True,
        )
    )
    db.commit()
    captured = {item.code: item.status for item in service.knowledge_map(actor)}
    assert captured["pathology.cell-injury.reversible"] == "weak"


def test_exit_quiz_is_retired_even_with_historical_formal_evidence(client, db) -> None:
    seed_showcase_case(db)
    headers = {"Authorization": f"Bearer {_student_token(client)}"}
    student = db.scalar(select(User).where(User.external_id == "t08-student"))
    state = ReviewState(
        student_id=student.id,
        card_code="historical:reversible",
        point_code="pathology.cell-injury.reversible",
        due_at=NOW,
    )
    db.add(state)
    db.commit()
    response = client.post(
        "/learning/exit-quiz", headers=headers, json={"topic_codes": ["pathology.cell-injury.reversible"]}
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "RETIRED_FLOW"
    assert db.get(ReviewState, state.id) is not None
    dashboard = client.get("/learning/review-dashboard", headers=headers)
    assert dashboard.json() == {"due_count": 0, "weak_point_codes": [], "items": []}


def test_conversation_learning_context_is_persisted_and_catalog_validated(client) -> None:
    headers = {"Authorization": f"Bearer {_student_token(client)}"}
    created = client.post(
        "/conversations",
        headers=headers,
        json={
            "client_id": "t08-context",
            "messages": [{"role": "user", "content": "解释肺炎的学习重点"}],
            "topic_codes": ["pathology.cell-injury.reversible"],
        },
    )
    assert created.status_code == 200
    assert created.json()["topic_codes"] == ["pathology.cell-injury.reversible"]
    reloaded = client.get("/conversations/by-client/t08-context", headers=headers)
    assert reloaded.status_code == 200 and reloaded.json()["topic_codes"] == ["pathology.cell-injury.reversible"]
    context = client.get(f"/conversations/{created.json()['id']}/learning-context", headers=headers)
    assert context.status_code == 200 and context.json()["topic_codes"] == ["pathology.cell-injury.reversible"]
    changed = client.put(
        f"/conversations/{created.json()['id']}/learning-context",
        headers=headers,
        json={"topic_codes": ["pathology.inflammation.vascular"]},
    )
    assert changed.status_code == 200 and changed.json()["topic_codes"] == ["pathology.inflammation.vascular"]
    preserved = client.get("/conversations/by-client/t08-context", headers=headers)
    assert preserved.status_code == 200 and len(preserved.json()["messages"]) == 1

    rejected = client.post(
        "/conversations",
        headers=headers,
        json={"client_id": "t08-invalid", "topic_codes": ["model-invented-code"]},
    )
    assert rejected.status_code == 422


def test_conversation_summaries_filter_by_confirmed_topic_without_breaking_pagination(client) -> None:
    headers = {"Authorization": f"Bearer {_student_token(client)}"}
    for client_id, topic_code in (
        ("t08-history-cap", "pathology.cell-injury.reversible"),
        ("t08-history-acs", "pathology.inflammation.vascular"),
    ):
        created = client.post(
            "/conversations",
            headers=headers,
            json={
                "client_id": client_id,
                "messages": [{"role": "user", "content": client_id}],
                "topic_codes": [topic_code],
            },
        )
        assert created.status_code == 200

    page = client.get(
        "/conversations/summaries?limit=20&offset=0&knowledge_point_code=pathology.cell-injury.reversible",
        headers=headers,
    )
    assert page.status_code == 200
    assert page.json()["total"] == 1
    assert page.json()["items"][0]["client_id"] == "t08-history-cap"
    assert page.json()["items"][0]["topic_codes"] == ["pathology.cell-injury.reversible"]


def test_teacher_contribution_creation_is_retired(client) -> None:
    teacher_headers = {"Authorization": f"Bearer {_teacher_token(client, 't08-card-author')}"}
    payload = {
        "point_code": "pathology.cell-injury.reversible",
        "card_type": "single_choice",
        "prompt": "课堂补充题",
        "options": ["生命体征", "爱好"],
        "correct_option": 0,
        "explanation": "说明",
        "reference": "教材",
    }
    created = client.post("/knowledge/teacher/cards", headers=teacher_headers, json=payload)
    assert created.status_code == 409
    assert created.json()["detail"]["code"] == "RETIRED_FLOW"
    student_headers = {"Authorization": f"Bearer {_student_token(client)}"}
    assert client.get("/knowledge/cards", headers=student_headers).json() == []


def test_problem_knowledge_binding_is_public_but_rejects_unknown_catalog_codes(client) -> None:
    headers = {"Authorization": f"Bearer {_teacher_token(client, 't08-problem-author')}"}
    from tests.test_t63_content_learning_pruning import _case_payload

    payload = {
        **_case_payload(client, headers, "knowledge-binding"),
        "knowledge_point_codes": ["pathology.cell-injury.reversible"],
    }
    created = client.post("/problems", headers=headers, json=payload)
    assert created.status_code == 200 and created.json()["knowledge_point_codes"] == [
        "pathology.cell-injury.reversible"
    ]
    invalid = client.post(
        "/problems",
        headers=headers,
        json={**payload, "title": "无效绑定", "knowledge_point_codes": ["fabricated-code"]},
    )
    assert invalid.status_code == 422


def test_regular_qa_reports_no_longer_create_teacher_review_items(client) -> None:
    student_headers = {"Authorization": f"Bearer {_student_token(client)}"}
    conversation = client.post(
        "/conversations",
        headers=student_headers,
        json={"client_id": "t08-report-review", "messages": [{"role": "user", "content": "病例推理记录"}]},
    )
    assert conversation.status_code == 200
    report = client.post(
        "/reports",
        headers=student_headers,
        json={
            "conversation_id": conversation.json()["id"],
            "ai_score": 62,
            "ai_summary": "需要进一步巩固鉴别要点。",
        },
    )
    assert report.status_code == 409
    assert report.json()["detail"]["code"] == "STATE_CONFLICT"
    dashboard = client.get("/learning/review-dashboard", headers=student_headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["weak_point_codes"] == []


def test_class_knowledge_analytics_is_teacher_scoped_and_hides_small_group_rankings(client) -> None:
    owner_headers = {"Authorization": f"Bearer {_teacher_token(client, 't08-analytics-owner')}"}
    created = client.post("/classes", headers=owner_headers, json={"name": "知识巩固班", "code": "t08-knowledge"})
    assert created.status_code == 200
    class_id = created.json()["id"]
    summary = client.get(f"/analytics/classes/{class_id}/knowledge", headers=owner_headers)
    assert summary.status_code == 200
    assert summary.json()["participant_count"] == 0
    assert summary.json()["knowledge"] == []
    assert summary.json()["schema_version"] == 3
    assert "weak_points" not in summary.json() and "rankings_suppressed" not in summary.json()

    other_headers = {"Authorization": f"Bearer {_teacher_token(client, 't08-analytics-other')}"}
    assert client.get(f"/analytics/classes/{class_id}/knowledge", headers=other_headers).status_code == 404


def test_recall_card_reveal_and_rate_are_retired(client) -> None:
    student_headers = {"Authorization": f"Bearer {_student_token(client)}"}
    for path, payload in [
        ("/learning/recall-cards/1/reveal", None),
        ("/learning/recall-cards/1/rate", {"rating": "good"}),
    ]:
        response = client.post(path, headers=student_headers, json=payload)
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "RETIRED_FLOW"
