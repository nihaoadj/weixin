from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.content.domain.knowledge_catalog import CARDS, POINTS
from app.modules.learning.application.knowledge_review import KnowledgeReviewApplication
from app.modules.learning.application.review_records import ReviewItemRecord, ReviewStateRecord
from app.shared.actor import Actor
from app.shared.errors import AppError

ACTOR = Actor(7, "student-7", "student", "学生")


class Uow:
    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1


class Repository:
    def __init__(self) -> None:
        self.state: ReviewStateRecord | None = None
        self.items: list[ReviewItemRecord] = []
        self.attempts: list[tuple[int, bool, str]] = []

    def get_state(self, _student_id: int, _card_code: str) -> ReviewStateRecord | None:
        return self.state

    def due_states(self, _student_id: int, _now: datetime, _limit: int) -> tuple[ReviewStateRecord, ...]:
        return (self.state,) if self.state else ()

    def list_states(self, _student_id: int) -> tuple[ReviewStateRecord, ...]:
        return (self.state,) if self.state else ()

    def save_state(self, state: ReviewStateRecord) -> ReviewStateRecord:
        self.state = ReviewStateRecord(
            1,
            state.student_id,
            state.card_code,
            state.point_code,
            state.due_at,
            state.interval_days,
            state.ease,
            state.repetitions,
            state.lapses,
            state.last_rating,
            state.last_reviewed_at,
        )
        return self.state

    def add_attempt(self, _student_id: int, _state_id: int, selected_option: int, correct: bool, rating: str) -> None:
        self.attempts.append((selected_option, correct, rating))

    def upsert_item(
        self,
        _student_id: int,
        point_code: str,
        card_code: str | None,
        source_type: str,
        source_id: str,
        note: str,
    ) -> ReviewItemRecord:
        item = ReviewItemRecord(1, point_code, card_code, source_type, source_id, note, True, NOW, NOW)
        self.items = [item]
        return item

    def list_items(self, _student_id: int, active_only: bool = True) -> tuple[ReviewItemRecord, ...]:
        return tuple(self.items if active_only else self.items)

    def dismiss_item(self, _student_id: int, _item_id: int) -> bool:
        return bool(self.items)


NOW = datetime(2026, 8, 31, tzinfo=UTC)


def test_versioned_pathology_catalog_has_five_topics_and_thirty_points() -> None:
    assert len(POINTS) == 30 and len(CARDS) == 120
    assert {point.system for point in POINTS} == {
        "pathology.cell-injury",
        "pathology.inflammation",
        "pathology.repair",
        "pathology.circulatory",
        "pathology.neoplasm",
    }
    assert all(sum(point.system == system for point in POINTS) == 6 for system in {point.system for point in POINTS})
    assert {card.point_code for card in CARDS} == {point.code for point in POINTS}


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


def test_exit_quiz_never_exposes_answers_and_wrong_answer_creates_review_evidence() -> None:
    repository = Repository()
    uow = Uow()
    service = KnowledgeReviewApplication(repository, uow)

    quiz = service.exit_quiz(ACTOR, ("pathology.cell-injury.reversible",))
    assert len(quiz) == 2
    assert not hasattr(quiz[0], "correct_option") and len(quiz[0].options) == 4

    result = service.grade(ACTOR, quiz[0].card_code, 0, "high")
    assert result.correct is False and result.rating == "again"
    assert repository.state is not None and repository.state.interval_days == 1
    assert repository.items[0].point_code == "pathology.cell-injury.reversible"
    assert uow.commits == 1


def test_review_rejects_unknown_topic_and_wrong_role() -> None:
    service = KnowledgeReviewApplication(Repository(), Uow())
    with pytest.raises(AppError) as unknown:
        service.exit_quiz(ACTOR, ("model-invented-code",))
    assert unknown.value.code == "VALIDATION_ERROR"
    with pytest.raises(AppError) as forbidden:
        service.dashboard(Actor(8, "teacher", "teacher", "教师"))
    assert forbidden.value.code == "ROLE_REQUIRED"


def test_knowledge_map_uses_student_review_evidence_not_catalog_browsing() -> None:
    repository = Repository()
    service = KnowledgeReviewApplication(repository, Uow())
    initial = {item.code: item.status for item in service.knowledge_map(ACTOR)}
    assert initial["pathology.cell-injury.reversible"] == "not_started"

    service.capture(ACTOR, "pathology.cell-injury.reversible", "assistant_message", "message-1", "")
    captured = {item.code: item.status for item in service.knowledge_map(ACTOR)}
    assert captured["pathology.cell-injury.reversible"] == "weak"


def test_review_http_contract_hides_answer_until_grade(client) -> None:
    headers = {"Authorization": f"Bearer {_student_token(client)}"}
    response = client.post(
        "/learning/exit-quiz", headers=headers, json={"topic_codes": ["pathology.cell-injury.reversible"]}
    )
    assert response.status_code == 200
    card = response.json()["cards"][0]
    assert card["point_code"] == "pathology.cell-injury.reversible"
    assert "correct_option" not in card and "explanation" not in card

    graded = client.post(
        f"/learning/reviews/{card['card_code']}/grade",
        headers=headers,
        json={"selected_option": 0, "confidence": "high"},
    )
    assert graded.status_code == 200
    assert graded.json()["correct"] is False and graded.json()["rating"] == "again"
    dashboard = client.get("/learning/review-dashboard", headers=headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["weak_point_codes"] == ["pathology.cell-injury.reversible"]


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


def test_teacher_contribution_requires_medical_approval_before_student_visibility(client) -> None:
    teacher_headers = {"Authorization": f"Bearer {_teacher_token(client, 't08-card-author')}"}
    payload = {
        "point_code": "pathology.cell-injury.reversible",
        "card_type": "single_choice",
        "prompt": "课堂补充题：哪项是教学情境中的优先公开评估线索？",
        "options": ["生命体征", "爱好"],
        "correct_option": 0,
        "explanation": "生命体征有助于进行初步风险识别。",
        "reference": "校内教研组审核材料",
    }
    created = client.post("/knowledge/teacher/cards", headers=teacher_headers, json=payload)
    assert created.status_code == 200 and created.json()["status"] == "draft"
    card_id = created.json()["id"]
    assert client.post(f"/knowledge/teacher/cards/{card_id}/submit", headers=teacher_headers).status_code == 200

    student_headers = {"Authorization": f"Bearer {_student_token(client)}"}
    before = client.get("/knowledge/cards?point_code=pathology.cell-injury.reversible", headers=student_headers)
    assert before.status_code == 200 and before.json() == []

    reviewer_headers = {"Authorization": f"Bearer {_teacher_token(client, 'demo_reviewer')}"}
    queue = client.get("/knowledge/review-queue", headers=reviewer_headers)
    assert queue.status_code == 200 and queue.json()[0]["id"] == card_id
    approved = client.post(
        f"/knowledge/teacher/cards/{card_id}/review",
        headers=reviewer_headers,
        json={"decision": "approved", "comment": "可用于教学"},
    )
    assert approved.status_code == 200 and approved.json()["status"] == "approved"

    visible = client.get("/knowledge/cards?point_code=pathology.cell-injury.reversible", headers=student_headers)
    assert visible.status_code == 200
    assert visible.json()[0]["correct_option"] is None and visible.json()[0]["explanation"] == ""
    quiz = client.post(
        "/learning/exit-quiz", headers=student_headers, json={"topic_codes": ["pathology.cell-injury.reversible"]}
    )
    assert quiz.status_code == 200
    teacher_card = next(item for item in quiz.json()["cards"] if item["card_code"] == f"teacher-choice:{card_id}")
    assert "correct_option" not in teacher_card and "explanation" not in teacher_card
    graded = client.post(
        f"/learning/reviews/{teacher_card['card_code']}/grade",
        headers=student_headers,
        json={"selected_option": 1, "confidence": "high"},
    )
    assert graded.status_code == 200 and graded.json()["correct"] is False
    revised = client.put(
        f"/knowledge/teacher/cards/{card_id}",
        headers=teacher_headers,
        json={**payload, "prompt": "课堂补充题（修订版）：优先公开评估什么？"},
    )
    assert revised.status_code == 200
    assert revised.json()["version"] == 2 and revised.json()["status"] == "draft"


def test_problem_knowledge_binding_is_public_but_rejects_unknown_catalog_codes(client) -> None:
    headers = {"Authorization": f"Bearer {_teacher_token(client, 't08-problem-author')}"}
    payload = {
        "type": "讨论题",
        "title": "肺炎知识点绑定题",
        "description": "从病例线索组织学习性解释。",
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


def test_teacher_review_topics_are_catalog_validated_and_create_student_review_items(client) -> None:
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
    assert report.status_code == 200
    report_id = report.json()["id"]
    assert client.post(f"/reports/{report_id}/submit", headers=student_headers).status_code == 200

    teacher_headers = {"Authorization": f"Bearer {_teacher_token(client, 't08-report-teacher')}"}
    reviewed = client.post(
        f"/reports/{report_id}/review",
        headers=teacher_headers,
        json={
            "teacher_score": 68,
            "teacher_feedback": "请复习并重组支持肺炎诊断的线索。",
            "review_topic_codes": ["pathology.cell-injury.reversible"],
        },
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["review_topic_codes"] == ["pathology.cell-injury.reversible"]
    dashboard = client.get("/learning/review-dashboard", headers=student_headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["weak_point_codes"] == ["pathology.cell-injury.reversible"]

    invalid = client.post(
        f"/reports/{report_id}/review",
        headers=teacher_headers,
        json={"teacher_score": 68, "teacher_feedback": "", "review_topic_codes": ["invented-topic"]},
    )
    assert invalid.status_code == 422


def test_class_knowledge_analytics_is_teacher_scoped_and_hides_small_group_rankings(client) -> None:
    owner_headers = {"Authorization": f"Bearer {_teacher_token(client, 't08-analytics-owner')}"}
    created = client.post("/classes", headers=owner_headers, json={"name": "知识巩固班", "code": "t08-knowledge"})
    assert created.status_code == 200
    class_id = created.json()["id"]
    summary = client.get(f"/analytics/classes/{class_id}/knowledge", headers=owner_headers)
    assert summary.status_code == 200
    assert summary.json()["participant_count"] == 0
    assert summary.json()["weak_points"] == [] and summary.json()["rankings_suppressed"] is True

    other_headers = {"Authorization": f"Bearer {_teacher_token(client, 't08-analytics-other')}"}
    assert client.get(f"/analytics/classes/{class_id}/knowledge", headers=other_headers).status_code == 404


def test_approved_recall_card_reveals_then_self_rates_without_objective_answer(client) -> None:
    teacher_headers = {"Authorization": f"Bearer {_teacher_token(client, 't08-recall-author')}"}
    created = client.post(
        "/knowledge/teacher/cards",
        headers=teacher_headers,
        json={
            "point_code": "pathology.cell-injury.reversible",
            "card_type": "recall",
            "prompt": "不看资料，概述肺炎教学病例中的优先评估线索。",
            "options": [],
            "correct_option": None,
            "explanation": "应先组织生命体征、氧合和危险信号等公开教学线索。",
            "reference": "校内教研组审核材料",
        },
    )
    assert created.status_code == 200
    card_id = created.json()["id"]
    assert client.post(f"/knowledge/teacher/cards/{card_id}/submit", headers=teacher_headers).status_code == 200
    student_headers = {"Authorization": f"Bearer {_student_token(client)}"}
    assert client.post(f"/learning/recall-cards/{card_id}/reveal", headers=student_headers).status_code == 404

    reviewer_headers = {"Authorization": f"Bearer {_teacher_token(client, 'demo_reviewer')}"}
    assert (
        client.post(
            f"/knowledge/teacher/cards/{card_id}/review",
            headers=reviewer_headers,
            json={"decision": "approved", "comment": "可用于主动回忆"},
        ).status_code
        == 200
    )
    revealed = client.post(f"/learning/recall-cards/{card_id}/reveal", headers=student_headers)
    assert revealed.status_code == 200
    assert revealed.json()["explanation"] and "correct_option" not in revealed.json()
    rated = client.post(f"/learning/recall-cards/{card_id}/rate", headers=student_headers, json={"rating": "good"})
    assert rated.status_code == 200 and rated.json()["rating"] == "good"
