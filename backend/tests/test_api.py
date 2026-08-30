from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


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
    assert report_response.status_code == 200
    report_id = report_response.json()["id"]
    assert report_response.json()["analysis"]["errors"][0]["content"] == "缺少鉴别诊断"

    submit_response = client.post(f"/reports/{report_id}/submit", headers={"Authorization": f"Bearer {student_token}"})
    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "pending_review"

    review_response = client.post(
        f"/reports/{report_id}/review",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={"teacher_score": 0, "teacher_feedback": "需要补充依据"},
    )
    assert review_response.status_code == 200
    assert review_response.json()["status"] == "reviewed"
    assert review_response.json()["teacher_score"] == 0

    duplicate_response = client.post(
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
    assert duplicate_response.status_code == 200
    assert duplicate_response.json()["status"] == "reviewed"
    assert duplicate_response.json()["analysis"]["strengths"] == ["结构清晰"]


def test_problem_publish_and_question_thread_flow() -> None:
    student_token = login()
    teacher_token = login("teacher", "demo_teacher")

    create_response = client.post(
        "/problems",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={
            "type": "医学常识",
            "title": "肺炎有哪些典型表现",
            "description": "请从临床表现和鉴别诊断回答",
            "target": "all",
            "target_label": "全体学生",
            "target_ids": [],
        },
    )
    assert create_response.status_code == 200
    problem_id = create_response.json()["id"]
    assert create_response.json()["status"] == "draft"

    student_before_publish = client.get("/problems", headers={"Authorization": f"Bearer {student_token}"})
    assert student_before_publish.status_code == 200
    assert student_before_publish.json() == []

    publish_response = client.post(
        f"/problems/{problem_id}/publish", headers={"Authorization": f"Bearer {teacher_token}"}
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "published"

    student_problems = client.get("/problems", headers={"Authorization": f"Bearer {student_token}"})
    assert student_problems.status_code == 200
    assert len(student_problems.json()) == 1

    thread_response = client.post(
        f"/problems/{problem_id}/thread",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"messages": [{"role": "user", "content": "需要结合发热、咳嗽、影像学改变进行判断"}]},
    )
    assert thread_response.status_code == 200
    assert thread_response.json()["question_id"] == problem_id

    teacher_problems = client.get("/problems", headers={"Authorization": f"Bearer {teacher_token}"})
    assert teacher_problems.status_code == 200
    assert teacher_problems.json()[0]["answer_count"] == 1


def test_class_and_individual_problem_visibility() -> None:
    class_student = login("student", "class_student", ["class_a"])
    other_student = login("student", "other_student", ["class_b"])
    teacher_token = login("teacher", "visibility_teacher")

    def create_and_publish(target: str, target_ids: list[str], title: str) -> int:
        created = client.post(
            "/problems",
            headers={"Authorization": f"Bearer {teacher_token}"},
            json={
                "type": "病例分析",
                "title": title,
                "description": "visibility test",
                "target": target,
                "target_label": title,
                "target_ids": target_ids,
            },
        )
        problem_id = created.json()["id"]
        published = client.post(
            f"/problems/{problem_id}/publish",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )
        assert published.status_code == 200
        return problem_id

    class_problem_id = create_and_publish("class", ["class_a"], "class only")
    individual_problem_id = create_and_publish("individual", ["other_student"], "student only")

    class_items = client.get("/problems", headers={"Authorization": f"Bearer {class_student}"}).json()
    other_items = client.get("/problems", headers={"Authorization": f"Bearer {other_student}"}).json()
    assert {item["id"] for item in class_items} == {class_problem_id}
    assert {item["id"] for item in other_items} == {individual_problem_id}

    hidden = client.get(
        f"/problems/{individual_problem_id}",
        headers={"Authorization": f"Bearer {class_student}"},
    )
    assert hidden.status_code == 404


def test_student_problem_response_does_not_expose_targeting_metadata() -> None:
    student_token = login("student", "target_metadata_student", ["class_a"])
    teacher_token = login("teacher", "target_metadata_teacher")
    created = client.post(
        "/problems",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={
            "type": "医学常识",
            "title": "定向题目",
            "description": "仅用于指定班级",
            "target": "class",
            "target_label": "临床一班",
            "target_ids": ["class_a", "other-class"],
        },
    )
    problem_id = created.json()["id"]
    assert (
        client.post(
            f"/problems/{problem_id}/publish",
            headers={"Authorization": f"Bearer {teacher_token}"},
        ).status_code
        == 200
    )

    response = client.get("/problems", headers={"Authorization": f"Bearer {student_token}"})

    item = next(item for item in response.json() if item["id"] == problem_id)
    assert item["target_ids"] == []
    assert item["target_label"] == "已分配学习内容"
    assert item["author_id"] is None
    assert item["capability_tags"] == []


def test_teacher_cannot_review_a_draft_report() -> None:
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
    response = client.post(
        f"/reports/{report.json()['id']}/review",
        headers={"Authorization": f"Bearer {teacher_token}"},
        json={"teacher_score": 70, "teacher_feedback": "not ready"},
    )
    assert response.status_code == 409
