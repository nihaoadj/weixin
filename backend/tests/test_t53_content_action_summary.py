"""Minimal Content todo counts preserve ownership and medical-review permissions."""

from sqlalchemy import select

from app.modules.classroom.infrastructure.models import MedicalReview
from app.modules.content.domain.digest import case_digest
from app.modules.content.infrastructure.models import KnowledgeCardContribution, Problem
from app.modules.identity.infrastructure.models import User
from tests.test_pbl_api import _headers, _login


def test_content_action_summary_has_only_owned_action_counts_and_no_body(client, db):
    owner = _login(client, "teacher", "t53-content-owner")
    other = _login(client, "teacher", "t53-content-other")
    student = _login(client, "student", "t53-content-student")
    owner_id = db.scalar(select(User.id).where(User.external_id == "t53-content-owner"))
    other_id = db.scalar(select(User.id).where(User.external_id == "t53-content-other"))

    def problem(author, kind="question", status="draft", medical="not_submitted"):
        item = Problem(
            author_id=author,
            content_type=kind,
            type="医学常识",
            title="PRIVATE_TITLE",
            description="PRIVATE_BODY",
            status=status,
            medical_review_status=medical,
            case_definition={"schema_version": "case_v2"} if kind == "guided_case" else None,
            rubric={"dimensions": []} if kind == "guided_case" else None,
        )
        db.add(item)
        db.flush()
        return item

    problem(owner_id)
    problem(owner_id, status="rejected")
    problem(owner_id, status="published")
    problem(other_id)
    problem(None)  # Unclaimed history is not the current teacher's todo.
    problem(owner_id, "guided_case")
    problem(owner_id, "guided_case", medical="rejected")
    problem(owner_id, "guided_case", medical="pending")
    problem(other_id, "guided_case", medical="pending")
    approved = problem(owner_id, "guided_case", medical="approved")
    valid = MedicalReview(
        problem_id=approved.id,
        reviewer_id=other_id,
        decision="approved",
        problem_version=1,
        case_digest=case_digest(approved),
    )
    db.add(valid)
    stale = problem(owner_id, "guided_case", medical="approved")
    db.add(
        MedicalReview(
            problem_id=stale.id, reviewer_id=other_id, decision="approved", problem_version=1, case_digest="0" * 64
        )
    )
    for author, status, source in [
        (owner_id, "draft", None),
        (owner_id, "rejected", None),
        (owner_id, "pending", None),
        (other_id, "pending", None),
        (owner_id, "draft", "pbl_ai"),
        (other_id, "pending", "pbl_ai"),
    ]:
        db.add(
            KnowledgeCardContribution(
                owner_id=author,
                point_code="pathology.inflammation.vascular",
                status=status,
                source_type=source,
                card_type="recall",
                prompt="PRIVATE_CARD",
                explanation="PRIVATE_ANSWER",
            )
        )
    db.commit()
    path = "/problems/teacher-action-summary"
    response = client.get(path, headers=_headers(owner))
    assert response.status_code == 200, response.text
    value = response.json()
    assert value == {
        "cases_draft": 0,
        "cases_rejected": 0,
        "cases_approved": 0,
        "questions_draft": 0,
        "questions_rejected": 0,
        "cards_draft": 0,
        "cards_rejected": 0,
        "medical_cases_pending": None,
        "medical_cards_pending": None,
        "as_of": value["as_of"],
    }
    assert "PRIVATE" not in response.text
    assert client.get(path, headers=_headers(student)).status_code == 403
    assert client.get(path).status_code == 401
    other_value = client.get(path, headers=_headers(other)).json()
    assert other_value["questions_draft"] == 0 and other_value["cards_draft"] == 0

    teacher = db.get(User, owner_id)
    teacher.permissions = ["medical_review"]
    db.commit()
    reviewer_value = client.get(path, headers=_headers(owner)).json()
    assert reviewer_value["medical_cases_pending"] == 0
    assert reviewer_value["medical_cards_pending"] == 0
    own_resources = client.get("/problems", headers=_headers(owner))
    assert own_resources.status_code == 200, own_resources.text
    actions = {item["id"]: item["allowed_actions"] for item in own_resources.json()}
    assert actions[approved.id] == ["edit", "delete"]
    assert actions[stale.id] == ["edit", "delete"]
    for item in own_resources.json():
        if item["author_id"] == other_id:
            assert item["allowed_actions"] == []
        if (
            item["author_id"] == owner_id
            and item["content_type"] == "guided_case"
            and item["medical_review_status"] == "pending"
        ):
            assert item["allowed_actions"] == ["edit", "delete"]
        if item["author_id"] == owner_id and item["content_type"] == "question" and item["status"] == "draft":
            assert item["allowed_actions"] == ["edit", "publish", "reject"]
    other_resources = client.get("/problems", headers=_headers(other)).json()
    assert all(item["id"] != approved.id for item in other_resources)
    published_question = problem(owner_id, status="published")
    db.commit()
    student_resources = client.get("/problems", headers=_headers(student)).json()
    assert all(item["id"] != published_question.id for item in student_resources)
    # A later edit invalidates approval without inventing a publishable todo.
    approved.description = "changed"
    db.commit()
    assert client.get(path, headers=_headers(owner)).json()["cases_approved"] == 0
    assert client.get(f"/problems/{approved.id}", headers=_headers(owner)).json()["allowed_actions"] == [
        "edit",
        "delete",
    ]
