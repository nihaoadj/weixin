from unittest.mock import MagicMock

from app.modules.pbl.application.records import InferenceRequest, InferenceResult, LearningResponseRecord
from app.modules.pbl.infrastructure.checked_gateway import CheckedGateway
from app.modules.pbl.infrastructure.providers.response_renderer import render_learning_response


def _phase_result(phase="problem_framing", decision="advance", evidence=("new",), status="probing"):
    response = LearningResponseRecord(
        opening="继续完成当前阶段。",
        key_points=("依据必须来自当前阶段的学生表达。",),
        next_step="请补充依据。",
    )
    return InferenceResult(
        assistant_reply=render_learning_response(response),
        diagnostic_status=status,
        response_sections=response,
        diagnosis_outcome="no_clear_gaps" if status == "ready" else None,
        phase_assessment={
            "phase": phase,
            "decision": decision,
            "evidence_message_ids": list(evidence),
            "evidence_summary": "当前阶段证据摘要。",
            "missing_elements": [],
        },
        schema_version=8,
    )


def _request(phase="problem_framing"):
    return InferenceRequest(
        session_id=1,
        topic_code="pathology.inflammation",
        question="当前回答",
        history=(
            {"id": "old", "role": "student", "content": "旧证据", "request_revision": 1},
            {"id": "recent", "role": "student", "content": "新证据", "request_revision": 3},
        ),
        message_id="new",
        current_phase=phase,
        phase_started_revision=2,
        current_revision=4,
        allowed_points=({"code": "pathology.inflammation.vascular", "title": "炎症血管反应"},),
        schema_version=8,
    )


def test_phase_gateway_rejects_old_evidence_mismatch_and_early_completion() -> None:
    for invalid in (
        _phase_result(evidence=("old",)),
        _phase_result(phase="hypothesis"),
        _phase_result(decision="complete", status="ready"),
    ):
        gateway = MagicMock()
        gateway.infer.return_value = invalid
        checked = CheckedGateway(gateway).infer(_request())
        assert checked.schema_version == 8
        assert checked.diagnostic_status == "unavailable"
        assert not checked.knowledge_gaps and not checked.reasoning_issues


def test_phase_gateway_accepts_current_stage_evidence_and_synthesis_completion() -> None:
    gateway = MagicMock()
    gateway.infer.return_value = _phase_result()
    advanced = CheckedGateway(gateway).infer(_request())
    assert advanced.schema_version == 8
    assert advanced.phase_assessment["decision"] == "advance"

    response = LearningResponseRecord(
        opening="形成结构化学习线索。",
        key_points=("当前综合回答暴露薄弱点。",),
        next_step="继续巩固目标。",
    )
    gateway.infer.return_value = InferenceResult(
        assistant_reply=render_learning_response(response),
        diagnostic_status="ready",
        response_sections=response,
        schema_version=8,
        diagnosis_outcome="identified_gaps",
        knowledge_gaps=(
            {
                "id": "gap",
                "point_code": "pathology.inflammation.vascular",
                "summary": "机制解释不足",
                "confidence": "medium",
                "evidence_message_ids": ["new"],
                "evidence_summary": "当前综合回答暴露薄弱点。",
            },
        ),
        phase_assessment={
            "phase": "synthesis",
            "decision": "complete",
            "evidence_message_ids": ["new"],
            "evidence_summary": "完成综合解释。",
            "missing_elements": [],
        },
    )
    completed = CheckedGateway(gateway).infer(_request("synthesis"))
    assert completed.schema_version == 8
    assert completed.diagnostic_status == "ready"
    assert completed.diagnosis_outcome == "identified_gaps"
