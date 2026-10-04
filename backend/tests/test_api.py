from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def login(role: str = "student", external_id: str = "demo_student", class_ids: list[str] | None = None) -> str:
    response = client.post(
        "/auth/demo-login",
        json={
            "role": role,
            "external_id": external_id,
            "nickname": role,
            "avatar_url": "",
            "class_ids": class_ids or [],
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_health() -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_medical_chat_requires_auth() -> None:
    response = client.post("/v1/medical-chat", json={"prompt": "高血压标准是什么"})
    assert response.status_code == 401


def test_medical_chat_emergency_response() -> None:
    token = login()
    response = client.post(
        "/v1/medical-chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": "胸口持续压榨样疼痛两个小时"},
    )
    assert response.status_code == 200
    assert "120" in response.json()["content"]


def test_demo_login_rejects_role_escalation() -> None:
    login("student", "same_account")
    response = client.post(
        "/auth/demo-login",
        json={"role": "teacher", "external_id": "same_account", "nickname": "teacher", "avatar_url": ""},
    )
    assert response.status_code == 409


def test_teacher_cannot_use_student_conversation_routes() -> None:
    teacher_token = login("teacher", "teacher_only")
    response = client.get("/conversations", headers={"Authorization": f"Bearer {teacher_token}"})
    assert response.status_code == 403


def test_conversation_isolation_between_students() -> None:
    first_token = login("student", "student_one")
    second_token = login("student", "student_two")
    created = client.post(
        "/conversations",
        headers={"Authorization": f"Bearer {first_token}"},
        json={"client_id": "private-conversation", "messages": [{"role": "user", "content": "private"}]},
    )
    conversation_id = created.json()["id"]

    response = client.get(
        f"/conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {second_token}"},
    )
    assert response.status_code == 404


def test_report_state_flow() -> None:
    student_token = login()
    teacher_token = login("teacher", "demo_teacher")

    conversation_response = client.post(
        "/conversations",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"client_id": "conv_1", "messages": [{"role": "user", "content": "肺炎如何诊断"}]},
    )
    assert conversation_response.status_code == 200
    conversation_id = conversation_response.json()["id"]

    report_response = client.post(
        "/reports",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "conversation_id": conversation_id,
            "ai_score": 88,
            "ai_summary": "结构完整",
            "analysis": {
                "errors": [{"content": "缺少鉴别诊断", "suggestion": "补充鉴别依据"}],
                "strengths": ["结构清晰"],
                "general_suggestions": ["继续练习"],
            },
        },
    )
    assert report_response.status_code == 409
    assert report_response.json()["detail"]["code"] == "STATE_CONFLICT"
    assert client.get("/reports/summaries", headers={"Authorization": f"Bearer {teacher_token}"}).status_code == 404


def test_open_discussion_create_and_thread_writes_are_retired() -> None:
    student = {"Authorization": f"Bearer {login()}"}
    teacher = {"Authorization": f"Bearer {login('teacher', 'demo_teacher')}"}
    payload = {"type": "医学常识", "title": "旧讨论题", "description": "旧内容"}
    for path, headers, body in [("/problems", teacher, payload), ("/problems/1/thread", student, {"messages": []})]:
        response = client.post(path, headers=headers, json=body)
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "RETIRED_FLOW"
    assert client.get("/student/questions", headers=student).json() == []
    assert client.get("/problems/1/thread", headers=student).status_code == 404


def test_case_writes_require_author_ownership() -> None:
    owner_headers = {"Authorization": f"Bearer {login('teacher', 'question_owner')}"}
    other_headers = {"Authorization": f"Bearer {login('teacher', 'question_intruder')}"}
    from tests.test_t63_content_learning_pruning import _case_payload

    payload = _case_payload(client, owner_headers, "ownership-case")
    created = client.post("/problems", headers=owner_headers, json=payload)
    assert created.status_code == 200
    problem_id = created.json()["id"]
    assert created.json()["author_id"] is not None
    assert client.put(f"/problems/{problem_id}", headers=other_headers, json=payload).status_code == 404
    assert client.post(f"/problems/{problem_id}/publish", headers=other_headers).status_code == 404
    assert client.post(f"/problems/{problem_id}/reject", headers=other_headers).status_code == 404
    assert client.put(f"/problems/{problem_id}", headers=owner_headers, json=payload).status_code == 200
    assert client.post(f"/problems/{problem_id}/publish", headers=owner_headers).status_code == 409


def test_class_and_individual_case_visibility(db) -> None:
    from app.modules.content.infrastructure.models import Problem

    class_student = login("student", "class_student", ["class_a"])
    other_student = login("student", "other_student", ["class_b"])
    cases = [
        Problem(
            type="病例分析",
            title="class only",
            content_type="guided_case",
            status="published",
            medical_review_status="approved",
            target="class",
            target_ids="class_a",
        ),
        Problem(
            type="病例分析",
            title="student only",
            content_type="guided_case",
            status="published",
            medical_review_status="approved",
            target="individual",
            target_ids="other_student",
        ),
    ]
    db.add_all(cases)
    db.commit()
    class_items = client.get("/problems", headers={"Authorization": f"Bearer {class_student}"}).json()
    other_items = client.get("/problems", headers={"Authorization": f"Bearer {other_student}"}).json()
    assert {item["id"] for item in class_items} == {cases[0].id}
    assert {item["id"] for item in other_items} == {cases[1].id}
    assert (
        client.get(f"/problems/{cases[1].id}", headers={"Authorization": f"Bearer {class_student}"}).status_code == 404
    )


def test_student_case_response_does_not_expose_targeting_metadata(db) -> None:
    from app.modules.content.infrastructure.models import Problem

    student_token = login("student", "target_metadata_student", ["class_a"])
    login("teacher", "target_metadata_teacher")
    case = Problem(
        type="病例分析",
        title="定向病例",
        content_type="guided_case",
        status="published",
        medical_review_status="approved",
        target="class",
        target_label="临床一班",
        target_ids="class_a,other-class",
    )
    db.add(case)
    db.commit()
    response = client.get("/problems", headers={"Authorization": f"Bearer {student_token}"})
    item = next(item for item in response.json() if item["id"] == case.id)
    assert item["target_ids"] == []
    assert item["target_label"] == "已分配学习内容"
    assert item["author_id"] is None
    assert item["capability_tags"] == []


def test_teacher_cannot_see_or_review_a_draft_report() -> None:
    student_token = login("student", "draft_student")
    teacher_token = login("teacher", "draft_teacher")
    conversation = client.post(
        "/conversations",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"client_id": "draft-conversation", "messages": [{"role": "user", "content": "answer"}]},
    )
    report = client.post(
        "/reports",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"conversation_id": conversation.json()["id"], "ai_score": 70, "ai_summary": "draft"},
    )
    assert report.status_code == 409
    assert report.json()["detail"]["code"] == "STATE_CONFLICT"
    # The old teacher route remains a deprecated compatibility endpoint and
    # cannot be used to review a retained report.
    assert client.get("/reports/1", headers={"Authorization": f"Bearer {teacher_token}"}).status_code == 404
    response = client.post(
        "/reports/1/review",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={"teacher_score": 70, "teacher_feedback": "not ready"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "STATE_CONFLICT"
