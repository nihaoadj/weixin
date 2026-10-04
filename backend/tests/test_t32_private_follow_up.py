from sqlalchemy import func, select

from app.modules.content.infrastructure.models import KnowledgeCardContribution
from app.modules.learning.infrastructure.evidence_models import LearningEvidenceEvent
from app.modules.pbl.infrastructure.models import (
    PblDiagnosticSnapshot,
    PblMessage,
    PblParticipation,
    PblPrivateFollowUpResult,
)
from tests.test_pbl_api import _classroom, _configure_gateway, _headers, _login, _session_payload
from tests.test_t17_unified_dialogues import _create_dialogue


def _complete(client, token: str, session_id: int, prefix: str = "t32"):
    endpoint = f"/student/learning-dialogues/{session_id}/messages"
    response = None
    for index in range(4):
        response = client.post(
            endpoint,
            headers=_headers(token),
            json={
                "client_message_id": f"{prefix}-{index}",
                "content": f"合成学生证据 {index}",
                "interaction_style": "guided",
            },
        )
        assert response.status_code == 200
    assert response.json()["phase_status"] == "completed"
    return response


def test_private_follow_up_freezes_diagnostic_and_is_idempotent(client, db, monkeypatch):
    gateway = _configure_gateway(monkeypatch)
    student = _login(client, "student", "t32-private")
    created = _create_dialogue(client, student, None, style="guided").json()
    session_id = created["session"]["id"]
    completed = _complete(client, student, session_id)
    endpoint = f"/student/learning-dialogues/{session_id}/messages"
    completion = completed.json()["diagnostic"]
    part = db.scalar(select(PblParticipation))
    frozen = (
        part.current_phase,
        part.phase_started_revision,
        part.phase_status,
        part.phase_completed_at,
        part.completion_snapshot_id,
        part.evidence_completed_revision,
    )
    before = {
        "snapshots": db.scalar(select(func.count(PblDiagnosticSnapshot.id))),
        "evidence": db.scalar(select(func.count(LearningEvidenceEvent.id))),
        "knowledge_cards": db.scalar(select(func.count(KnowledgeCardContribution.id))),
    }

    payload = {
        "client_message_id": "private-1",
        "content": "PRIVATE_SENTINEL：请再解释血管通透性。",
        "interaction_style": "direct",
    }
    first = client.post(endpoint, headers=_headers(student), json=payload)
    assert first.status_code == 200
    value = first.json()
    assert value["response_kind"] == value["turn_scope"] == "private_follow_up"
    assert value["conversation_mode"] == "private_follow_up" and value["evidence_locked"] is True
    assert value["diagnostic"] == completion
    assert value["private_follow_up"]["processing_status"] == "completed"
    assert [item["turn_scope"] for item in value["messages"][-2:]] == [
        "private_follow_up",
        "private_follow_up",
    ]
    assert value["messages"][-1]["reply_to_message_id"] == int(value["messages"][-2]["id"])

    db.expire_all()
    part = db.get(PblParticipation, part.id)
    assert (
        part.current_phase,
        part.phase_started_revision,
        part.phase_status,
        part.phase_completed_at,
        part.completion_snapshot_id,
        part.evidence_completed_revision,
    ) == frozen
    assert db.scalar(select(func.count(PblDiagnosticSnapshot.id))) == before["snapshots"]
    assert db.scalar(select(func.count(LearningEvidenceEvent.id))) == before["evidence"]
    assert db.scalar(select(func.count(KnowledgeCardContribution.id))) == before["knowledge_cards"]
    assert db.scalar(select(func.count(PblPrivateFollowUpResult.id))) == 1

    repeated = client.post(endpoint, headers=_headers(student), json=payload)
    assert repeated.status_code == 200
    assert repeated.json()["private_follow_up"] == value["private_follow_up"]
    assert gateway.private_calls == 1
    assert client.post(endpoint, headers=_headers(student), json=payload | {"content": "changed"}).status_code == 409
    assert (
        client.post(endpoint, headers=_headers(student), json=payload | {"interaction_style": "guided"}).status_code
        == 409
    )

    final_retry = client.post(
        endpoint,
        headers=_headers(student),
        json={"client_message_id": "t32-3", "content": "合成学生证据 3", "interaction_style": "guided"},
    )
    assert final_retry.status_code == 200
    assert final_retry.json()["response_kind"] == "evidence_assessment"
    assert final_retry.json()["diagnostic"]["id"] == completion["id"]
    assert gateway.calls == 4


def test_closed_completed_can_continue_but_closed_active_cannot(client, db, monkeypatch):
    gateway = _configure_gateway(monkeypatch)
    teacher = _login(client, "teacher", "t32-owner")
    student = _login(client, "student", "t32-student")
    outsider = _login(client, "student", "t32-outsider")
    class_id = _classroom(client, teacher, "t32-student")
    session_id = client.post(
        f"/classes/{class_id}/pbl-sessions", headers=_headers(teacher), json=_session_payload(db)
    ).json()["id"]
    completed = _complete(client, student, session_id, "closed-complete").json()
    snapshot_id = completed["diagnostic"]["id"]
    before_dashboard = client.get(
        f"/classes/{class_id}/pbl-sessions/{session_id}/dashboard", headers=_headers(teacher)
    ).json()
    assert (
        client.post(f"/classes/{class_id}/pbl-sessions/{session_id}/close", headers=_headers(teacher)).status_code
        == 200
    )
    endpoint = f"/student/learning-dialogues/{session_id}/messages"
    private = client.post(
        endpoint,
        headers=_headers(student),
        json={
            "client_message_id": "closed-private",
            "content": "PRIVATE_CLOSED_SENTINEL",
            "interaction_style": "direct",
        },
    )
    assert private.status_code == 200 and private.json()["diagnostic"]["id"] == snapshot_id
    assert (
        client.post(
            endpoint,
            headers=_headers(outsider),
            json={"client_message_id": "outsider", "content": "越权", "interaction_style": "guided"},
        ).status_code
        == 404
    )
    teacher_json = client.get("/teacher/pbl-diagnostics", headers=_headers(teacher)).text
    assert "PRIVATE_CLOSED_SENTINEL" not in teacher_json
    after_dashboard = client.get(
        f"/classes/{class_id}/pbl-sessions/{session_id}/dashboard", headers=_headers(teacher)
    ).json()
    assert after_dashboard["students"][0].get("last_activity_at") == before_dashboard["students"][0].get(
        "last_activity_at"
    )
    assert gateway.private_calls == 1

    second_session = client.post(
        f"/classes/{class_id}/pbl-sessions", headers=_headers(teacher), json=_session_payload(db)
    ).json()["id"]
    assert (
        client.post(f"/classes/{class_id}/pbl-sessions/{second_session}/close", headers=_headers(teacher)).status_code
        == 200
    )
    blocked = client.post(
        f"/student/learning-dialogues/{second_session}/messages",
        headers=_headers(student),
        json={"client_message_id": "closed-active", "content": "不能继续", "interaction_style": "guided"},
    )
    assert blocked.status_code == 404


def test_broken_completion_locator_blocks_private_provider(client, db, monkeypatch):
    gateway = _configure_gateway(monkeypatch)
    student = _login(client, "student", "t32-broken")
    created = _create_dialogue(client, student, None, style="guided").json()
    session_id = created["session"]["id"]
    _complete(client, student, session_id, "broken")
    part = db.scalar(select(PblParticipation))
    part.completion_snapshot_id = None
    db.commit()
    blocked = client.post(
        f"/student/learning-dialogues/{session_id}/messages",
        headers=_headers(student),
        json={"client_message_id": "private", "content": "should not call", "interaction_style": "guided"},
    )
    assert blocked.status_code == 409
    assert gateway.private_calls == 0
    assert db.scalar(select(func.count(PblMessage.id)).where(PblMessage.turn_scope == "private_follow_up")) == 0
