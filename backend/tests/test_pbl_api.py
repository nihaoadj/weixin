from sqlalchemy import func, select

from app.modules.content.infrastructure.models import Problem, ProblemOrigin
from app.modules.identity.infrastructure.models import User
from app.modules.pbl.application.records import InferenceRequest, InferenceResult
from app.modules.pbl.infrastructure.models import PblParticipation, PblQuestionSuggestion
from app.modules.pbl.infrastructure.repositories import SqlAlchemyPblRepository


def _login(client, role: str, external_id: str) -> str:
    response = client.post(
        "/auth/demo-login",
        json={"role": role, "external_id": external_id, "nickname": external_id, "avatar_url": "", "class_ids": []},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class _ReadyGateway:
    calls = 0

    def infer(self, request: InferenceRequest) -> InferenceResult:
        from app.modules.pbl.wiring import LocalMockGateway

        self.calls += 1
        return LocalMockGateway().infer(request)


def _configure_gateway(monkeypatch) -> _ReadyGateway:
    gateway = _ReadyGateway()
    monkeypatch.setattr("app.modules.pbl.wiring._gateway", lambda: (gateway, "coze", "bot"))
    return gateway


def _classroom(client, teacher_token: str, student_external_id: str) -> int:
    created = client.post("/classes", headers=_headers(teacher_token), json={"name": "PBL 一班", "code": "pbl-a"})
    assert created.status_code == 200
    class_id = created.json()["id"]
    added = client.post(
        f"/classes/{class_id}/members",
        headers=_headers(teacher_token),
        json={"student_external_id": student_external_id},
    )
    assert added.status_code == 204
    from app.bootstrap.seed import seed_showcase_case
    from app.db import SessionLocal

    with SessionLocal() as session:
        seed_showcase_case(session)
    return class_id


def _session_payload(db):
    return {
        "topic_code": "pathology.inflammation",
        "case_id": db.scalar(select(Problem.id).where(Problem.slug == "pathology.inflammation-showcase")),
        "goal_point_codes": ["pathology.inflammation.vascular"],
    }


def test_pbl_student_visibility_idempotency_and_close(client, db, monkeypatch) -> None:
    gateway = _configure_gateway(monkeypatch)
    teacher = _login(client, "teacher", "pbl-teacher")
    student = _login(client, "student", "pbl-student")
    class_id = _classroom(client, teacher, "pbl-student")
    created = client.post(
        f"/classes/{class_id}/pbl-sessions",
        headers=_headers(teacher),
        json=_session_payload(db),
    )
    assert created.status_code == 201
    session_id = created.json()["id"]
    assert client.get("/student/pbl-sessions", headers=_headers(student)).json()[0]["id"] == session_id

    payload = {"client_message_id": "once", "content": "红肿说明一定是感染吗？"}
    first = client.post(f"/student/pbl-sessions/{session_id}/messages", headers=_headers(student), json=payload)
    second = client.post(f"/student/pbl-sessions/{session_id}/messages", headers=_headers(student), json=payload)
    assert first.status_code == second.status_code == 200
    assert gateway.calls == 1
    student_diagnostic = first.json()["diagnostic"]
    assert "recommended_questions" not in student_diagnostic
    assert "provider_metadata" not in student_diagnostic

    outsider = _login(client, "student", "pbl-outsider")
    assert client.get("/student/pbl-sessions", headers=_headers(outsider)).json() == []
    assert (
        client.get(f"/student/pbl-sessions/{session_id}/participation", headers=_headers(outsider)).status_code == 404
    )

    student_id = db.scalar(select(User.id).where(User.external_id == "pbl-student"))
    assert student_id is not None
    assert client.delete(f"/classes/{class_id}/members/{student_id}", headers=_headers(teacher)).status_code == 204
    assert client.get(f"/student/pbl-sessions/{session_id}/participation", headers=_headers(student)).status_code == 200

    closed = client.post(f"/classes/{class_id}/pbl-sessions/{session_id}/close", headers=_headers(teacher))
    assert closed.status_code == 200
    assert (
        client.post(f"/classes/{class_id}/pbl-sessions/{session_id}/close", headers=_headers(teacher)).status_code
        == 200
    )
    assert (
        client.post(
            f"/student/pbl-sessions/{session_id}/messages",
            headers=_headers(student),
            json={"client_message_id": "new-after-close", "content": "closed"},
        ).status_code
        == 404
    )


def test_pbl_teacher_scope_edit_protection_and_adoption_idempotency(client, db, monkeypatch) -> None:
    _configure_gateway(monkeypatch)
    teacher = _login(client, "teacher", "pbl-owner")
    other_teacher = _login(client, "teacher", "pbl-other")
    student = _login(client, "student", "pbl-owner-student")
    class_id = _classroom(client, teacher, "pbl-owner-student")
    session_id = client.post(
        f"/classes/{class_id}/pbl-sessions",
        headers=_headers(teacher),
        json=_session_payload(db),
    ).json()["id"]
    for index, content in enumerate(("为什么红肿？", "提出血管机制假设。", "比较支持与反对证据。", "整合机制与疑问。")):
        response = client.post(
            f"/student/pbl-sessions/{session_id}/messages",
            headers=_headers(student),
            json={"client_message_id": f"phase-{index}", "content": content},
        )
        assert response.status_code == 200
    queue = client.get("/teacher/pbl-diagnostics", headers=_headers(teacher))
    assert queue.status_code == 200
    suggestion = queue.json()["items"][0]["recommended_questions"][0]
    suggestion_id = suggestion["id"]
    assert (
        client.get(
            f"/teacher/pbl-diagnostics/{queue.json()['items'][0]['id']}", headers=_headers(other_teacher)
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/teacher/pbl-question-suggestions/{suggestion_id}",
            headers=_headers(other_teacher),
            json={"version": suggestion["version"], "title": "x", "prompt": "x", "reject": False},
        ).status_code
        == 404
    )

    edited = client.patch(
        f"/teacher/pbl-question-suggestions/{suggestion_id}",
        headers=_headers(teacher),
        json={"version": suggestion["version"], "title": "教师修订题", "prompt": "请区分血管反应。", "reject": False},
    )
    assert edited.status_code == 200
    assert edited.json()["status"] == "edited"

    latest = client.get("/teacher/pbl-diagnostics", headers=_headers(teacher)).json()["items"][0][
        "recommended_questions"
    ][0]
    publish = {"version": latest["version"], "title": "教师当前编辑", "prompt": "请区分血管反应。"}
    suggestion_id = latest["id"]
    adopted = client.post(
        f"/teacher/pbl-question-suggestions/{suggestion_id}/adopt-and-publish", headers=_headers(teacher), json=publish
    )
    repeated = client.post(
        f"/teacher/pbl-question-suggestions/{suggestion_id}/adopt-and-publish", headers=_headers(teacher), json=publish
    )
    assert adopted.status_code == repeated.status_code == 200
    assert adopted.json()["problem_id"] == repeated.json()["problem_id"]
    db.expire_all()
    assert db.scalar(select(func.count(Problem.id))) == 6
    assert db.scalar(select(func.count(ProblemOrigin.id))) == 1
    stored = db.get(PblQuestionSuggestion, suggestion_id)
    assert stored is not None and stored.status == "published"


def test_pbl_repository_rejects_a_stale_inference_revision(client, db, monkeypatch) -> None:
    _configure_gateway(monkeypatch)
    teacher = _login(client, "teacher", "pbl-revision-owner")
    student = _login(client, "student", "pbl-revision-student")
    class_id = _classroom(client, teacher, "pbl-revision-student")
    session_id = client.post(
        f"/classes/{class_id}/pbl-sessions",
        headers=_headers(teacher),
        json=_session_payload(db),
    ).json()["id"]
    client.get(f"/student/pbl-sessions/{session_id}/participation", headers=_headers(student))
    student_id = db.scalar(select(User.id).where(User.external_id == "pbl-revision-student"))
    participation = db.scalar(
        select(PblParticipation).where(
            PblParticipation.session_id == session_id,
            PblParticipation.student_id == student_id,
        )
    )
    assert participation is not None
    repository = SqlAlchemyPblRepository(db)
    first = repository.append_student_message(participation.id, "revision-first", "第一条")
    assert first is not None
    import pytest

    from app.shared.errors import AppError

    with pytest.raises(AppError, match="上一条消息"):
        repository.append_student_message(participation.id, "revision-second", "第二条")
    # Simulate a revision change by a separate writer; the result CAS must consult persisted state.
    participation.revision += 1
    db.flush()
    stale = repository.save_result(
        participation.id,
        first.revision,
        InferenceResult("过期结果", "probing", follow_up_question="继续说明依据。"),
    )
    assert stale is None


def test_t14_participation_advances_four_phases_and_locks_new_messages(client, db, monkeypatch) -> None:
    gateway = _configure_gateway(monkeypatch)
    teacher = _login(client, "teacher", "t14-phase-teacher")
    student = _login(client, "student", "t14-phase-student")
    class_id = _classroom(client, teacher, "t14-phase-student")
    session_id = client.post(
        f"/classes/{class_id}/pbl-sessions",
        headers=_headers(teacher),
        json=_session_payload(db),
    ).json()["id"]
    path = f"/student/pbl-sessions/{session_id}/messages"
    expected = ["hypothesis", "evidence", "synthesis", "completed"]
    last = None
    for index, phase in enumerate(expected):
        last = client.post(
            path,
            headers=_headers(student),
            json={"client_message_id": f"stage-{index}", "content": f"第 {index + 1} 阶段的新证据"},
        )
        assert last.status_code == 200, last.text
        assert last.json()["current_phase"] == phase
    assert gateway.calls == 4
    assert last is not None and last.json()["diagnostic"]["diagnostic_status"] == "ready"
    duplicate = client.post(
        path,
        headers=_headers(student),
        json={"client_message_id": "stage-3", "content": "第 4 阶段的新证据"},
    )
    assert duplicate.status_code == 200 and duplicate.json() == last.json()
    assert gateway.calls == 4
    assert (
        client.post(
            path,
            headers=_headers(student),
            json={"client_message_id": "after-complete", "content": "完成后的新消息"},
        ).status_code
        == 409
    )
    sessions = client.get(f"/classes/{class_id}/pbl-sessions", headers=_headers(teacher)).json()
    assert sessions[0]["phase_counts"]["completed"] == 1
