from __future__ import annotations

import json
from dataclasses import dataclass

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.db import SessionLocal
from app.modules.content.application.records import CaseDraftResult
from app.modules.content.application.use_cases import ContentApplication
from app.modules.content.domain.defaults import deterministic_case_draft
from app.modules.content.domain.templates import SAFETY_NOTICE, showcase_draft
from app.modules.content.infrastructure.ai_schemas import CaseDraftModel
from app.modules.content.infrastructure.draft_generator import CaseDraftAiGateway
from app.modules.identity.infrastructure.models import User
from app.modules.training.infrastructure.models import AICallLog
from app.platform.ai import AICallResult
from app.shared.actor import Actor
from app.shared.errors import AppError


def _login(client, external_id: str) -> str:
    response = client.post(
        "/auth/demo-login",
        json={"role": "teacher", "external_id": external_id, "nickname": "teacher", "avatar_url": ""},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_disabled_fallback_preserves_all_approved_topic_payloads_and_audit(client) -> None:
    token = _login(client, "content_draft_fallback")
    headers = {"Authorization": f"Bearer {token}"}
    expected = {
        "急性胸痛": {
            "title": "急性胸痛：危险分层与证据推理",
            "specialty": "心血管内科/急诊教学",
            "fact_ids": {
                "chest_onset",
                "chest_quality",
                "chest_associated",
                "chest_risk",
                "chest_vitals",
                "chest_ecg",
                "chest_troponin",
            },
            "reference_text": "需优先危险分层。",
        },
        "社区获得性肺炎": {
            "title": "社区获得性肺炎：结构化临床推理",
            "specialty": "呼吸内科",
            "fact_ids": {
                "history_onset",
                "history_sputum",
                "history_chest_pain",
                "history_risk",
                "history_allergy",
                "exam_vitals",
                "exam_lung",
                "test_cbc",
                "test_xray",
            },
            "reference_text": "首先考虑社区获得性肺炎。",
        },
        "右下腹痛": {
            "title": "右下腹痛：问题表征与检查选择",
            "specialty": "普通外科/急诊教学",
            "fact_ids": {"abd_migration", "abd_gi", "abd_fever", "abd_urinary", "abd_exam", "abd_blood", "abd_imaging"},
            "reference_text": "需结合适用性选择检查。",
        },
        "未知主题": {
            "title": "未知主题：结构化临床推理（待教师补全）",
            "specialty": "呼吸内科",
            "fact_ids": {
                "history_onset",
                "history_sputum",
                "history_chest_pain",
                "history_risk",
                "history_allergy",
                "exam_vitals",
                "exam_lung",
                "test_cbc",
                "test_xray",
            },
            "reference_text": "首先考虑社区获得性肺炎。",
        },
    }

    for topic, expectation in expected.items():
        response = client.post(
            "/problems/case-drafts/generate",
            headers=headers,
            json={
                "topic": topic,
                "learner_level": "undergraduate",
                "learning_objectives": ["识别危险信号", "说明证据"],
            },
        )
        assert response.status_code == 200
        body = response.json()
        definition = body["case_definition"]
        dimensions = body["rubric"]["dimensions"]
        assert body["title"] == expectation["title"]
        assert body["specialty"] == expectation["specialty"]
        assert body["description"].endswith("学习层级：undergraduate。教学目标：识别危险信号、说明证据")
        assert body["generation_mode"] == "fallback"
        assert body["safety_notice"] == SAFETY_NOTICE
        assert definition["schema_version"] == 2
        assert set(definition["stage_instructions"]) == {
            "history",
            "problem_representation",
            "differential",
            "tests",
            "management",
        }
        assert {item["id"] for item in definition["facts"]} == expectation["fact_ids"]
        assert expectation["reference_text"] in definition["reference_reasoning"]["problem_representation"]
        assert [item["id"] for item in dimensions] == [
            "information_gathering",
            "problem_representation",
            "differential_diagnosis",
            "evidence_reasoning",
            "test_selection",
            "management_safety",
        ]
        assert [item["weight"] for item in dimensions] == [20, 15, 20, 15, 15, 15]

    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.external_id == "content_draft_fallback"))
        assert user is not None
        logs = session.scalars(
            select(AICallLog).where(AICallLog.user_id == user.id, AICallLog.task == "case_draft")
        ).all()
        assert len(logs) == 4
        assert {(log.model_name, log.prompt_version, log.fallback_used, log.failure_reason) for log in logs} == {
            ("deterministic-fallback", get_settings().ai_prompt_version, True, "disabled")
        }


def test_model_success_uses_structured_provider_and_does_not_leak_metadata(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "ai_model", "content-model")
    template = showcase_draft("急性胸痛")
    calls: list[tuple[str, list[dict[str, str]], type[CaseDraftModel], float]] = []

    def fake_call(task, messages, response_schema, temperature):
        calls.append((task, messages, response_schema, temperature))
        return AICallResult(response_schema.model_validate(template), None, 23)

    monkeypatch.setattr("app.modules.content.infrastructure.draft_generator.call_structured", fake_call)
    result = CaseDraftAiGateway().generate("急性胸痛", "undergraduate", ["说明证据"], 42)

    assert result.payload == template
    assert set(result.payload) == {
        "title",
        "description",
        "specialty",
        "difficulty",
        "estimated_minutes",
        "case_definition",
        "rubric",
    }
    assert result.generation_mode == "model"
    assert result.model_name == "content-model"
    assert result.prompt_version == settings.ai_prompt_version
    assert result.fallback_used is False
    assert result.failure_reason is None
    assert calls[0][0] == "case_draft"
    assert calls[0][2] is CaseDraftModel
    assert calls[0][3] == 0.4
    request = json.loads(calls[0][1][1]["content"])
    assert request == {
        "topic": "急性胸痛",
        "learner_level": "undergraduate",
        "learning_objectives": ["说明证据"],
        "fixed_stages": ["history", "problem_representation", "differential", "tests", "management"],
    }
    assert "42" not in json.dumps(calls[0][1], ensure_ascii=False)


def test_provider_error_uses_the_same_legacy_fallback(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.modules.content.infrastructure.draft_generator.call_structured",
        lambda *_args, **_kwargs: AICallResult(None, "http_error", 11),
    )
    result = CaseDraftAiGateway().generate("未知主题", "undergraduate", ["说明证据"], 42)
    assert result.payload == deterministic_case_draft("未知主题", "undergraduate", ["说明证据"])
    assert result.generation_mode == "fallback"
    assert result.fallback_used is True
    assert result.failure_reason == "http_error"


@dataclass
class _FixedGenerator:
    result: CaseDraftResult

    def generate(self, _topic: str, _level: str, _objectives: list[str], _teacher_id: int) -> CaseDraftResult:
        return self.result


@dataclass
class _RecordingAudit:
    calls: int = 0
    fail: bool = False
    last_metadata: tuple[int, str, str, int, bool, str | None] | None = None

    def record_ai_call(
        self,
        *,
        user_id: int,
        model_name: str,
        prompt_version: str,
        latency_ms: int,
        fallback_used: bool,
        failure_reason: str | None,
    ) -> None:
        if self.fail:
            raise RuntimeError("audit failed")
        self.calls += 1
        self.last_metadata = (user_id, model_name, prompt_version, latency_ms, fallback_used, failure_reason)


@dataclass
class _RecordingUow:
    commits: int = 0
    rollbacks: int = 0
    fail_commit: bool = False

    def flush(self) -> None:
        pass

    def commit(self) -> None:
        self.commits += 1
        if self.fail_commit:
            raise RuntimeError("commit failed")

    def rollback(self) -> None:
        self.rollbacks += 1


def _application(uow: _RecordingUow, audit: _RecordingAudit) -> ContentApplication:
    result = CaseDraftResult(
        payload=showcase_draft("社区获得性肺炎"),
        generation_mode="fallback",
        safety_notice=SAFETY_NOTICE,
        failure_reason="disabled",
    )
    return ContentApplication(
        object(),
        uow,
        draft_generator=_FixedGenerator(result),
        draft_audit=audit,
    )


def _teacher() -> Actor:
    return Actor(id=7, external_id="draft-teacher", role="teacher", nickname="teacher")


def test_draft_audit_is_committed_by_the_application_uow() -> None:
    uow = _RecordingUow()
    audit = _RecordingAudit()
    result = _application(uow, audit).generate_draft(_teacher(), "肺炎", "本科生", ["说明证据"])
    assert result.generation_mode == "fallback"
    assert audit.calls == 1
    assert audit.last_metadata == (7, "deterministic-fallback", "case-v2", 0, True, "disabled")
    assert uow.commits == 1
    assert uow.rollbacks == 0


@pytest.mark.parametrize("failure", ["audit", "commit"])
def test_draft_transaction_failure_rolls_back_and_maps_to_service_error(failure: str) -> None:
    uow = _RecordingUow(fail_commit=failure == "commit")
    audit = _RecordingAudit(fail=failure == "audit")
    with pytest.raises(AppError) as error:
        _application(uow, audit).generate_draft(_teacher(), "肺炎", "本科生", ["说明证据"])
    assert (error.value.code, error.value.status_code) == ("SERVICE_ERROR", 503)
    assert uow.commits == (1 if failure == "commit" else 0)
    assert uow.rollbacks == 1
