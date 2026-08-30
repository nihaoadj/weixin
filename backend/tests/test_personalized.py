from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.services.case_seed import seed_showcase_case

client = TestClient(app)


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_showcase_case(db)
    finally:
        db.close()


def login(external_id: str = "personalized_student") -> dict[str, str]:
    response = client.post(
        "/auth/demo-login",
        json={"role": "student", "external_id": external_id, "nickname": external_id, "avatar_url": ""},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def complete_case(headers: dict[str, str], problem_id: int, retry_of_id: int | None = None) -> int:
    attempt = client.post(
        f"/problems/{problem_id}/attempts", headers=headers, json={"retry_of_id": retry_of_id}
    ).json()["id"]
    answers = [
        ("history", {"stage_id": "history", "summary": "发热咳嗽", "key_findings": ["发热"]}),
        ("problem_representation", {"stage_id": "problem_representation", "summary": "急性发热咳嗽"}),
        (
            "differential",
            {
                "stage_id": "differential",
                "items": [
                    {"diagnosis": "肺炎", "supporting_evidence": ["浸润"], "opposing_evidence": []},
                    {"diagnosis": "肺栓塞", "supporting_evidence": [], "opposing_evidence": ["咳痰"]},
                ],
            },
        ),
        (
            "tests",
            {"stage_id": "tests", "items": [{"test_name": "胸片", "rationale": "评估浸润", "priority": "necessary"}]},
        ),
        (
            "management",
            {
                "stage_id": "management",
                "items": [{"action": "评估氧合并监测", "rationale": "安全"}],
                "safety_considerations": ["复评"],
            },
        ),
    ]
    for stage, answer in answers:
        assert (
            client.post(
                f"/attempts/{attempt}/stages/{stage}/submit", headers=headers, json={"answer": answer}
            ).status_code
            == 200
        )
    assert client.post(f"/attempts/{attempt}/complete", headers=headers).status_code == 200
    return attempt


def test_plan_tasks_notifications_and_idempotency() -> None:
    headers = login()
    case = next(
        item for item in client.get("/problems", headers=headers).json() if item["slug"] == "cap-undergraduate-showcase"
    )
    source_attempt = complete_case(headers, case["id"])

    plan = client.get("/learning-plans/current", headers=headers)
    assert plan.status_code == 200
    data = plan.json()
    assert len(data["tasks"]) == 3
    assert client.post(f"/attempts/{source_attempt}/learning-plan", headers=headers).json()["id"] == data["id"]

    profile = client.get("/learning/profile", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["active_plan"]["id"] == data["id"]
    notifications = client.get("/notifications?unread_only=true", headers=headers)
    assert notifications.status_code == 200
    assert notifications.json()["unread_count"] >= 1

    first = data["tasks"][0]
    started = client.post(f"/learning-tasks/{first['id']}/start", headers=headers)
    assert started.status_code == 200
    retry_id = started.json()["attempt"]["id"]
    assert client.post(f"/learning-tasks/{first['id']}/start", headers=headers).json()["attempt"]["id"] == retry_id
    assert (
        client.post(
            f"/attempts/{retry_id}/stages/differential/submit",
            headers=headers,
            json={
                "answer": {
                    "stage_id": "differential",
                    "items": [
                        {"diagnosis": "肺炎", "supporting_evidence": ["浸润"], "opposing_evidence": []},
                        {"diagnosis": "肺栓塞", "supporting_evidence": [], "opposing_evidence": []},
                    ],
                }
            },
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/attempts/{retry_id}/stages/tests/submit",
            headers=headers,
            json={
                "answer": {
                    "stage_id": "tests",
                    "items": [{"test_name": "影像", "rationale": "评估", "priority": "necessary"}],
                }
            },
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/attempts/{retry_id}/stages/management/submit",
            headers=headers,
            json={
                "answer": {
                    "stage_id": "management",
                    "items": [{"action": "评估氧合", "rationale": "安全"}],
                    "safety_considerations": [],
                }
            },
        ).status_code
        == 200
    )
    assert client.post(f"/attempts/{retry_id}/complete", headers=headers).status_code == 200

    second = client.get("/learning-plans/current", headers=headers).json()["tasks"][1]
    assert client.post(f"/learning-tasks/{second['id']}/start", headers=headers).status_code == 200
    micro_id = client.post(f"/learning-tasks/{second['id']}/start", headers=headers).json()["attempt"]["id"]
    submitted = client.post(
        f"/learning-task-attempts/{micro_id}/submit",
        headers=headers,
        json={"answer": {"text": "依据证据说明危险并复评"}},
    )
    assert submitted.status_code == 200
    assert (
        client.post(
            f"/learning-task-attempts/{micro_id}/submit", headers=headers, json={"answer": {"text": "覆盖答案不应生效"}}
        ).json()["answer"]["text"]
        == "依据证据说明危险并复评"
    )
    third = client.get("/learning-plans/current", headers=headers).json()["tasks"][2]
    assert client.post(f"/learning-tasks/{third['id']}/start", headers=headers).status_code == 200
    assert client.post(f"/learning-tasks/{third['id']}/start", headers=headers).status_code == 200
    assert client.post(f"/learning-plans/{data['id']}/complete", headers=headers).status_code == 409
    assert client.post("/notifications/read-all", headers=headers).json()["marked"] >= 1
