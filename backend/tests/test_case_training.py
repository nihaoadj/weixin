import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
pytestmark = pytest.mark.seed_showcase


def _login(role: str, external_id: str) -> str:
    response = client.post(
        "/auth/demo-login",
        json={"role": role, "external_id": external_id, "nickname": role, "avatar_url": ""},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_structured_case_training_keeps_hidden_fields_private() -> None:
    case = client.get("/problems", headers={"Authorization": f"Bearer {_login('teacher', 'demo_teacher')}"}).json()[0]
    student = _login("student", "case_student")
    teacher = _login("teacher", "demo_teacher")
    headers = {"Authorization": f"Bearer {student}"}

    listing = client.get("/problems", headers=headers)
    assert listing.status_code == 200
    public_case = listing.json()[0]
    assert public_case["id"] == case["id"]
    assert "case_definition" not in public_case
    assert "facts" not in public_case
    assert client.get(f"/problems/{case['id']}/authoring", headers=headers).status_code == 403
    authoring = client.get(f"/problems/{case['id']}/authoring", headers={"Authorization": f"Bearer {teacher}"})
    assert "facts" in authoring.json()["case_definition"]

    started = client.post(f"/problems/{case['id']}/attempts", headers=headers, json={})
    assert started.status_code == 200
    attempt_id = started.json()["id"]
    patient = client.post(f"/attempts/{attempt_id}/messages", headers=headers, json={"content": "请说明切片形态观察。"})
    assert patient.status_code == 200
    assert authoring.json()["case_definition"]["facts"][1]["value"] in patient.json()["content"]
    assert "revealed_fact_ids" not in patient.json()

    submissions = [
        ("history", {"stage_id": "history", "summary": "异型性与基底膜浸润的形态观察", "key_findings": ["异型性"]}),
        ("problem_representation", {"stage_id": "problem_representation", "summary": "48岁男性急性发热咳嗽，考虑肺炎"}),
        (
            "differential",
            {
                "stage_id": "differential",
                "items": [
                    {"diagnosis": "社区获得性肺炎", "supporting_evidence": ["发热"], "opposing_evidence": ["无"]},
                    {"diagnosis": "病毒性肺炎", "supporting_evidence": ["发热"], "opposing_evidence": ["黄痰"]},
                ],
            },
        ),
        (
            "tests",
            {
                "stage_id": "tests",
                "items": [{"test_name": "胸部影像", "rationale": "确认浸润", "priority": "necessary"}],
            },
        ),
        (
            "management",
            {
                "stage_id": "management",
                "items": [{"action": "评估氧合和严重程度", "rationale": "保障安全"}],
                "safety_considerations": ["药物过敏"],
            },
        ),
    ]
    for stage, answer in submissions:
        response = client.post(
            f"/attempts/{attempt_id}/stages/{stage}/submit", headers=headers, json={"answer": answer}
        )
        assert response.status_code == 200

    report = client.post(f"/attempts/{attempt_id}/complete", headers=headers)
    assert report.status_code == 200
    assert len(report.json()["dimensions"]) == 6
    assert report.json()["fallback_used"] is True
    evidence = [snippet for dimension in report.json()["dimensions"] for snippet in dimension["evidence"]]
    assert any("异型性" in snippet or "基底膜" in snippet for snippet in evidence)
    assert all("命中" not in snippet for snippet in evidence)
    assert client.get(f"/attempts/{attempt_id}/assessment", headers=headers).status_code == 200
    assert client.post(f"/attempts/{attempt_id}/complete", headers=headers).status_code == 200
    assert client.get("/attempts", headers=headers).status_code == 200
    retry = client.post(
        f"/problems/{case['id']}/attempts",
        headers=headers,
        json={"retry_of_id": attempt_id},
    )
    assert retry.status_code == 200
    assert retry.json()["retry_of_id"] == attempt_id
