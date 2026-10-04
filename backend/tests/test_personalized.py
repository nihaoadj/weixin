"""Independent case analysis remains private and never creates a formal plan."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
pytestmark = pytest.mark.seed_showcase


def _login() -> dict[str, str]:
    response = client.post(
        "/auth/demo-login",
        json={
            "role": "student",
            "external_id": "personalized_student",
            "nickname": "personalized_student",
            "avatar_url": "",
        },
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _complete_case(headers: dict[str, str], problem_id: int) -> int:
    response = client.post(f"/problems/{problem_id}/attempts", headers=headers, json={"retry_of_id": None})
    assert response.status_code == 200
    attempt_id = response.json()["id"]
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
                f"/attempts/{attempt_id}/stages/{stage}/submit", headers=headers, json={"answer": answer}
            ).status_code
            == 200
        )
    assert client.post(f"/attempts/{attempt_id}/complete", headers=headers).status_code == 200
    return attempt_id


def test_independent_case_keeps_student_analysis_without_creating_formal_plan() -> None:
    headers = _login()
    case = next(
        item
        for item in client.get("/problems", headers=headers).json()
        if item["slug"] == "pathology.cell-injury-showcase"
    )
    attempt_id = _complete_case(headers, case["id"])

    assessment = client.get(f"/attempts/{attempt_id}/assessment", headers=headers)
    assert assessment.status_code == 200
    assert assessment.json()["summary"]
    assert client.get("/learning-plans/current", headers=headers).status_code == 404
    for _ in range(2):
        rejected = client.post(f"/attempts/{attempt_id}/learning-plan", headers=headers)
        assert rejected.status_code == 409
    assert client.get("/learning-plans/current", headers=headers).status_code == 404
    assert client.post(f"/attempts/{attempt_id}/complete", headers=headers).status_code == 200
    assert client.get(f"/attempts/{attempt_id}/assessment", headers=headers).status_code == 200
