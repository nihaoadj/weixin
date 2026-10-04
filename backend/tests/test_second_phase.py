import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
pytestmark = pytest.mark.seed_showcase


def login(role: str, external_id: str, class_ids: list[str] | None = None) -> str:
    response = client.post(
        "/auth/demo-login",
        json={
            "role": role,
            "external_id": external_id,
            "nickname": external_id,
            "avatar_url": "",
            "class_ids": class_ids or [],
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_classes_review_and_analytics_permissions() -> None:
    teacher = login("teacher", "demo_teacher")
    reviewer = login("teacher", "demo_reviewer")
    student = login("student", "analytics_student")
    teacher_headers = {"Authorization": f"Bearer {teacher}"}
    reviewer_headers = {"Authorization": f"Bearer {reviewer}"}
    student_id = client.post(
        "/auth/demo-login",
        json={"role": "student", "external_id": "analytics_student", "nickname": "学生", "avatar_url": ""},
    ).json()["user"]["id"]
    classes = client.get("/classes", headers=teacher_headers)
    assert classes.status_code == 200
    class_id = classes.json()[0]["id"]
    assert client.post(f"/classes/{class_id}/members/{student_id}", headers=teacher_headers).status_code == 204
    assert client.post(f"/classes/{class_id}/members/{student_id}", headers=teacher_headers).status_code == 204
    members = client.get(f"/classes/{class_id}/students", headers=teacher_headers).json()
    assert any(item["id"] == student_id for item in members)
    assert client.get("/classes", headers={"Authorization": f"Bearer {student}"}).status_code == 403
    assert client.get("/problems/review-queue", headers=teacher_headers).status_code == 403
    assert client.get("/problems/review-queue?status=approved", headers=reviewer_headers).status_code == 200
    showcase = client.get("/problems", headers=teacher_headers).json()[0]
    history = client.get(f"/problems/{showcase['id']}/medical-reviews", headers=reviewer_headers)
    assert history.status_code == 200
    student_headers = {"Authorization": f"Bearer {student}"}
    attempt = client.post(f"/problems/{showcase['id']}/attempts", headers=student_headers, json={}).json()["id"]
    stage_answers = [
        ("history", {"stage_id": "history", "summary": "发热", "key_findings": ["发热"]}),
        ("problem_representation", {"stage_id": "problem_representation", "summary": "发热咳嗽"}),
        ("differential", {"stage_id": "differential", "items": [{"diagnosis": "肺炎"}, {"diagnosis": "病毒感染"}]}),
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
    ]
    for stage, answer in stage_answers:
        response = client.post(
            f"/attempts/{attempt}/stages/{stage}/submit",
            headers=student_headers,
            json={"answer": answer},
        )
        assert response.status_code == 200
    assert client.post(f"/attempts/{attempt}/complete", headers=student_headers).status_code == 200
    overview = client.get(f"/analytics/overview?class_id={class_id}", headers=teacher_headers)
    assert overview.status_code == 200
    assert overview.json()["schema_version"] == 3
    assert overview.json()["completed_tests"] == 0
    assert overview.json()["completion_rate"] is None
    assert "improved_rate" not in overview.json()
    invalid_range = client.get("/analytics/overview?date_from=2026-08-24&date_to=2026-08-23", headers=teacher_headers)
    assert invalid_range.status_code == 400
    assert client.get("/analytics/overview?class_id=99999", headers=teacher_headers).status_code == 404


def test_class_crud_and_case_student_analytics() -> None:
    teacher = login("teacher", "demo_teacher")
    login("student", "case_analytics_student")
    headers = {"Authorization": f"Bearer {teacher}"}
    student_id = client.post(
        "/auth/demo-login",
        json={"role": "student", "external_id": "case_analytics_student", "nickname": "学生", "avatar_url": ""},
    ).json()["user"]["id"]
    created = client.post("/classes", headers=headers, json={"name": "分析班", "code": "analytics_class"})
    assert created.status_code == 200
    class_id = created.json()["id"]
    renamed = client.patch(f"/classes/{class_id}", headers=headers, json={"name": "分析班（春季）"})
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "分析班（春季）"
    assert client.post("/classes", headers=headers, json={"name": "重复", "code": "analytics_class"}).status_code == 409
    assert client.post(f"/classes/{class_id}/members/99999", headers=headers).status_code == 404
    assert client.post(f"/classes/{class_id}/members/{student_id}", headers=headers).status_code == 204
    assert (
        client.post(
            f"/classes/{class_id}/members",
            headers=headers,
            json={"student_external_id": "case_analytics_student"},
        ).status_code
        == 204
    )
    problems = client.get("/problems", headers=headers).json()
    case_id = next(item["id"] for item in problems if item["content_type"] == "guided_case")
    case_result = client.get(f"/analytics/cases/{case_id}?class_id={class_id}", headers=headers)
    assert case_result.status_code == 409
    student_result = client.get(f"/analytics/students/{student_id}?class_id={class_id}", headers=headers)
    assert student_result.status_code == 200
    assert student_result.json()["completed_tests"] == 0
    assert client.delete(f"/classes/{class_id}/members/{student_id}", headers=headers).status_code == 204
    assert client.delete(f"/classes/{class_id}/members/{student_id}", headers=headers).status_code == 204
    assert client.get(f"/analytics/students/99999?class_id={class_id}", headers=headers).status_code == 404
    archived = client.patch(f"/classes/{class_id}", headers=headers, json={"status": "archived"})
    assert archived.status_code == 200
    assert client.post(f"/classes/{class_id}/members/{student_id}", headers=headers).status_code == 409


def test_case_analytics_is_owner_scoped() -> None:
    owner = login("teacher", "analytics_owner")
    other = login("teacher", "analytics_other")
    owner_headers = {"Authorization": f"Bearer {owner}"}
    other_headers = {"Authorization": f"Bearer {other}"}
    generated = client.post(
        "/problems/case-drafts/generate",
        headers=owner_headers,
        json={"topic": "胸痛", "learner_level": "本科生", "learning_objectives": ["结构化评估"]},
    )
    assert generated.status_code == 200
    draft = generated.json()
    problem = client.post(
        "/problems",
        headers=owner_headers,
        json={
            "type": "病例分析",
            "title": draft["title"],
            "description": draft["description"],
            "target": "all",
            "target_label": "全体学生",
            "target_ids": [],
            "content_type": "guided_case",
            "slug": "owner-scoped-case",
            "specialty": draft["specialty"],
            "difficulty": draft["difficulty"],
            "estimated_minutes": draft["estimated_minutes"],
            "case_definition": draft["case_definition"],
            "rubric": draft["rubric"],
        },
    )
    assert problem.status_code == 200
    problem_id = problem.json()["id"]
    assert problem.json()["status"] == "published"
    assert problem.json()["medical_review_status"] == "not_required"
    assert client.get(f"/analytics/cases/{problem_id}", headers=other_headers).status_code == 404


def test_legacy_class_ids_and_class_members_are_unioned(db) -> None:
    teacher = login("teacher", "legacy_teacher")
    student = login("student", "legacy_student", ["legacy-code"])
    headers = {"Authorization": f"Bearer {teacher}"}
    classroom = client.post("/classes", headers=headers, json={"name": "兼容班", "code": "legacy-code"})
    assert classroom.status_code == 200
    from app.modules.content.infrastructure.models import Problem

    case = Problem(
        type="病例分析",
        title="legacy visible",
        content_type="guided_case",
        status="published",
        medical_review_status="approved",
        target="class",
        target_ids="legacy-code",
    )
    db.add(case)
    db.commit()
    problem_id = case.id
    visible = client.get("/problems", headers={"Authorization": f"Bearer {student}"})
    assert any(item["id"] == problem_id for item in visible.json())


def test_showcase_cases_have_distinct_target_facts_and_reference_paths() -> None:
    teacher = login("teacher", "demo_teacher")
    headers = {"Authorization": f"Bearer {teacher}"}
    cases = [case for case in client.get("/problems", headers=headers).json() if case["content_type"] == "guided_case"]
    assert len(cases) == 5
    definitions = [
        client.get(f"/problems/{case['id']}/authoring", headers=headers).json()["case_definition"] for case in cases
    ]
    assert len({definition["facts"][1]["value"] for definition in definitions}) == 5
    assert len({definition["reference_reasoning"]["problem_representation"] for definition in definitions}) == 5
    assert all(len(definition["practice_blueprints"]) == 6 for definition in definitions)
    assert all(len(case["knowledge_point_codes"]) == 6 for case in cases)
