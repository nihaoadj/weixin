import json
from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.modules.classroom.infrastructure.models import ClassRoom
from app.modules.identity.infrastructure.models import User
from app.modules.pbl.application.records import InferenceRequest
from app.modules.pbl.infrastructure.checked_gateway import CheckedGateway
from app.modules.pbl.infrastructure.models import PblMessage, PblParticipation, PblSession
from app.modules.pbl.infrastructure.provider_schema import ProviderPayloadV7
from app.modules.pbl.infrastructure.providers.coze_parser import parse_provider_json
from app.modules.pbl.infrastructure.providers.request_builder import provider_messages
from app.modules.pbl.infrastructure.repositories import SqlAlchemyPblRepository


def valid_no_clear_gaps() -> dict[str, object]:
    variant = {
        "title": "炎症目标验证",
        "prompt": "炎症渗出最直接的血管变化是什么？",
        "objective": "核对炎症机制",
        "options": ["通透性增加", "通透性降低"],
        "answer": 0,
        "explanation": "血管通透性增加使蛋白和液体外渗。",
    }
    return {
        "schema_version": 7,
        "interaction_style": "guided",
        "learning_response": {
            "opening": "讨论完成。",
            "key_points": ["已核对课堂目标。"],
            "next_step": "等待教师审阅。",
        },
        "diagnostic_status": "ready",
        "diagnosis_outcome": "no_clear_gaps",
        "knowledge_gaps": [],
        "reasoning_issues": [],
        "candidate_tasks": [
            {
                "candidate_key": "inflammation-check",
                "purpose": "goal_verification",
                "task_type": "retest",
                "point_codes": ["pathology.inflammation.vascular"],
                "dimension_ids": [],
                "linked_findings": [],
                "variants": [
                    {**variant, "cycle_number": 1},
                    {**variant, "cycle_number": 2, "prompt": "炎症时蛋白外渗主要反映哪一变化？"},
                ],
            }
        ],
        "recommended_knowledge_cards": [],
        "safety_notice": "仅供病理学教学。",
        "safety_status": "educational",
        "phase_assessment": {
            "phase": "synthesis",
            "decision": "complete",
            "evidence_message_ids": ["student-4"],
            "evidence_summary": "学生已完成综合阶段总结。",
            "missing_elements": [],
        },
    }


def test_no_clear_gaps_can_complete_without_invented_findings_or_cards() -> None:
    payload = ProviderPayloadV7.model_validate(valid_no_clear_gaps())
    assert payload.diagnosis_outcome == "no_clear_gaps"
    assert len(payload.candidate_tasks[0].variants) == 2


@pytest.mark.parametrize(
    "change",
    [
        lambda data: data["candidate_tasks"][0]["variants"].pop(),
        lambda data: data["candidate_tasks"].append(deepcopy(data["candidate_tasks"][0])),
        lambda data: data.update(knowledge_gaps=[{"id": "fake"}]),
        lambda data: data["candidate_tasks"][0].update(purpose="remediation"),
    ],
)
def test_invalid_no_clear_gaps_output_is_rejected(change) -> None:
    data = valid_no_clear_gaps()
    change(data)
    with pytest.raises(ValidationError):
        ProviderPayloadV7.model_validate(data)


def test_insufficient_evidence_cannot_create_confirmed_task() -> None:
    data = valid_no_clear_gaps()
    data["diagnostic_status"] = "insufficient_evidence"
    data["diagnosis_outcome"] = None
    data["phase_assessment"]["decision"] = "continue"
    with pytest.raises(ValidationError):
        ProviderPayloadV7.model_validate(data)


def v7_request(session_kind: str = "classroom") -> InferenceRequest:
    return InferenceRequest(
        session_id=11,
        topic_code="pathology.inflammation",
        question="我理解了炎症的血管变化",
        history=(),
        message_id="student-4",
        current_phase="synthesis",
        phase_started_revision=0,
        current_revision=1,
        goal_point_codes=("pathology.inflammation.vascular",) if session_kind == "classroom" else (),
        allowed_points=({"code": "pathology.inflammation.vascular", "title": "炎症血管反应"},),
        session_kind=session_kind,
        schema_version=7,
    )


class StubGateway:
    def __init__(self, result):
        self.result = result

    def infer(self, _request):
        return self.result


def test_v7_parser_is_history_compatible_but_online_gateway_requires_v8() -> None:
    data = valid_no_clear_gaps()
    parsed = parse_provider_json(json_text(data), {}, schema_version=7)
    assert parsed.schema_version == 7
    assert parsed.diagnosis_outcome == "no_clear_gaps"
    checked = CheckedGateway(StubGateway(parsed)).infer(v7_request())
    assert checked.diagnostic_status == "unavailable"
    assert checked.failure_reason == "unsupported_provider_schema"
    with pytest.raises(ValueError, match="unsupported provider schema"):
        provider_messages(v7_request())


def test_v7_schema_is_never_an_online_classroom_or_autonomous_fallback() -> None:
    data = valid_no_clear_gaps()
    parsed = parse_provider_json(json_text(data), {}, schema_version=7)
    for kind in ("classroom", "student_initiated"):
        checked = CheckedGateway(StubGateway(parsed)).infer(v7_request(kind))
        assert checked.diagnostic_status == "unavailable"
        assert checked.failure_reason == "unsupported_provider_schema"


def test_v7_historical_diagnosis_roundtrip_does_not_reactivate_candidate_tasks(db) -> None:
    teacher = User(external_id="t43-v7-teacher", role="teacher", nickname="教师")
    student = User(external_id="t43-v7-student", role="student", nickname="学生")
    db.add_all((teacher, student))
    db.flush()
    classroom = ClassRoom(name="炎症课堂", code="t43-v7", teacher_id=teacher.id)
    db.add(classroom)
    db.flush()
    session = PblSession(
        class_id=classroom.id,
        teacher_id=teacher.id,
        session_kind="classroom",
        topic_code="pathology.inflammation.vascular",
        goal_point_codes=["pathology.inflammation.vascular"],
        provider="local_mock",
    )
    db.add(session)
    db.flush()
    participation = PblParticipation(
        session_id=session.id, student_id=student.id, revision=1, current_phase="synthesis"
    )
    db.add(participation)
    db.flush()
    db.add(
        PblMessage(
            participation_id=participation.id,
            sequence=1,
            role="student",
            content="我理解了炎症血管变化。",
            interaction_style="guided",
            turn_scope="evidence",
            client_message_id="student-4",
            request_revision=1,
            processing_status="pending",
        )
    )
    db.flush()
    parsed = parse_provider_json(json_text(valid_no_clear_gaps()), {}, schema_version=7)
    snapshot = SqlAlchemyPblRepository(db).save_result(participation.id, 1, parsed)
    db.commit()
    assert snapshot is not None
    restored = SqlAlchemyPblRepository(db).completion_snapshot(participation.id)
    assert restored is not None
    assert restored.diagnosis_outcome == "no_clear_gaps"
    assert restored.schema_version == 7
    assert restored.candidate_tasks == ()


def json_text(data: dict[str, object]) -> str:
    return json.dumps(data, ensure_ascii=False)
