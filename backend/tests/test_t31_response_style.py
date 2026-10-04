import pytest
from sqlalchemy import select

from app.modules.pbl.infrastructure.models import PblDiagnosticSnapshot, PblMessage
from tests.test_pbl_api import _classroom, _configure_gateway, _headers, _login, _session_payload
from tests.test_t17_unified_dialogues import _create_dialogue


def test_mixed_turns_keep_identity_history_and_phase(client, db, monkeypatch):
    gateway = _configure_gateway(monkeypatch)
    student = _login(client, "student", "t31-mixed")
    created = _create_dialogue(client, student, None, style="guided").json()
    session_id = created["session"]["id"]
    endpoint = f"/student/learning-dialogues/{session_id}/messages"
    styles = ["guided", "direct", "guided"]
    snapshots = []
    for index, style in enumerate(styles):
        payload = {"client_message_id": f"turn-{index}", "content": f"合成阶段依据 {index}", "interaction_style": style}
        response = client.post(endpoint, headers=_headers(student), json=payload)
        assert response.status_code == 200
        value = response.json()
        assert value["interaction_style"] == style
        assert value["diagnostic"]["revision"] == index + 1
        assert value["diagnostic"]["interaction_style"] == style
        snapshots.append(value["diagnostic"]["id"])
        repeated = client.post(endpoint, headers=_headers(student), json=payload)
        assert repeated.status_code == 200
        assert repeated.json()["diagnostic"]["id"] == snapshots[-1]
        assert gateway.calls == index + 1
        for conflict in ({"interaction_style": "direct" if style == "guided" else "guided"}, {"content": "不同内容"}):
            assert client.post(endpoint, headers=_headers(student), json=payload | conflict).status_code == 409
    messages = db.scalars(select(PblMessage).order_by(PblMessage.sequence)).all()
    assert [message.interaction_style for message in messages] == [s for s in styles for _ in range(2)]
    records = db.scalars(select(PblDiagnosticSnapshot).order_by(PblDiagnosticSnapshot.revision)).all()
    assert [record.interaction_style for record in records] == styles


@pytest.mark.parametrize("style", ["guided", "direct"])
def test_first_classroom_message_creates_participation(client, db, monkeypatch, style):
    gateway = _configure_gateway(monkeypatch)
    teacher = _login(client, "teacher", "t31-owner")
    student = _login(client, "student", "t31-first")
    class_id = _classroom(client, teacher, "t31-first")
    session_id = client.post(
        f"/classes/{class_id}/pbl-sessions", headers=_headers(teacher), json=_session_payload(db)
    ).json()["id"]
    response = client.post(
        f"/student/learning-dialogues/{session_id}/messages",
        headers=_headers(student),
        json={"client_message_id": "first", "content": "合成课堂问题", "interaction_style": style},
    )
    assert response.status_code == 200
    assert response.json()["interaction_style"] == style
    assert gateway.calls == 1


def test_create_retry_does_not_rewrite_current_preference(client, monkeypatch):
    _configure_gateway(monkeypatch)
    student = _login(client, "student", "t31-create")
    first = _create_dialogue(client, student, None, style="direct")
    retry = _create_dialogue(client, student, None, style="guided")
    assert first.status_code == retry.status_code == 201
    assert retry.json()["session"]["id"] == first.json()["session"]["id"]
    assert retry.json()["participation"]["interaction_style"] == "direct"


@pytest.mark.parametrize("style", ["guided", "direct"])
def test_v8_response_is_rendered_deterministically(style):
    import json

    from app.modules.pbl.infrastructure.providers.coze_parser import parse_provider_json
    from tests.test_pbl_providers import READY_V8

    payload = json.loads(READY_V8)
    payload.update(
        schema_version=8,
        interaction_style=style,
        learning_response={"opening": "合成回应", "key_points": ["要点一", "要点二"], "next_step": "研讨已完成"},
    )
    result = parse_provider_json(json.dumps(payload), {}, schema_version=8)
    assert result.diagnostic_status == "ready"
    assert result.assistant_reply == "回应\n合成回应\n\n关键要点\n• 要点一\n• 要点二\n\n下一步\n研讨已完成"
    assert result.interaction_style == style
    assert result.follow_up_question is None


def test_turn_style_columns_are_persisted(db):
    from sqlalchemy import inspect

    for table in ("pbl_messages", "pbl_diagnostic_snapshots"):
        columns = {column["name"]: column for column in inspect(db.bind).get_columns(table)}
        assert "interaction_style" in columns
        assert columns["interaction_style"]["nullable"] is False


def test_repository_pending_style_conflicts_and_stale_recovery(client, db, monkeypatch):
    from datetime import UTC, datetime, timedelta

    from app.modules.pbl.application.records import InferenceResult
    from app.modules.pbl.infrastructure.repositories import SqlAlchemyPblRepository
    from app.shared.errors import AppError

    _configure_gateway(monkeypatch)
    student = _login(client, "student", "t31-pending")
    created = _create_dialogue(client, student, None, style="guided").json()
    from app.modules.pbl.infrastructure.models import PblParticipation

    part = db.scalar(select(PblParticipation))
    repository = SqlAlchemyPblRepository(db)
    pending = repository.append_student_message(part.id, "pending", "synthetic", "direct")
    assert pending.interaction_style == "direct"
    with pytest.raises(AppError):
        repository.append_student_message(part.id, "pending", "synthetic", "guided")
    with pytest.raises(AppError):
        repository.append_student_message(part.id, "other", "synthetic", "guided")
    with pytest.raises(AppError):
        repository.save_result(part.id, pending.revision, InferenceResult("mismatch", "unavailable"))
    message = db.scalar(select(PblMessage))
    message.created_at = datetime.now(UTC) - timedelta(seconds=90)
    db.flush()
    result = repository.message_result(part.id, "pending")
    assert result.turn_scope == "evidence"
    assert result.snapshot.interaction_style == "direct"
    assert result.snapshot.status == "unavailable"
    assert result.snapshot.knowledge_gaps == result.snapshot.reasoning_issues == ()
    assert repository.participation(part.id).current_phase == "problem_framing"
    assert created["session"]["id"] == part.session_id


def test_omitted_style_completed_retry_and_access_scope(client, monkeypatch):
    gateway = _configure_gateway(monkeypatch)
    student = _login(client, "student", "t31-compat")
    outsider = _login(client, "student", "t31-outsider")
    created = _create_dialogue(client, student, None, style="direct").json()
    endpoint = f"/student/learning-dialogues/{created['session']['id']}/messages"
    payload = {"client_message_id": "first", "content": "合成解释"}
    assert client.post(endpoint, headers=_headers(outsider), json=payload).status_code == 404
    first = client.post(endpoint, headers=_headers(student), json=payload)
    assert first.status_code == 200 and first.json()["interaction_style"] == "direct"
    for index in range(1, 4):
        response = client.post(endpoint, headers=_headers(student), json=payload | {"client_message_id": str(index)})
        assert response.status_code == 200
    assert response.json()["phase_status"] == "completed"
    private = client.post(endpoint, headers=_headers(student), json=payload | {"client_message_id": "new"})
    assert private.status_code == 200
    assert private.json()["response_kind"] == "private_follow_up"
    assert private.json()["diagnostic"]["id"] == response.json()["diagnostic"]["id"]
    repeated = client.post(endpoint, headers=_headers(student), json=payload)
    assert repeated.status_code == 200
    assert repeated.json()["diagnostic"]["id"] == first.json()["diagnostic"]["id"]
    assert gateway.calls == 4
    assert gateway.private_calls == 1
