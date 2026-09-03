from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.modules.content.application.use_cases import ContentApplication
from app.modules.content.domain.policy import ContentPolicy
from app.modules.learning.domain.policy import assess_micro, target_dimensions
from app.modules.qa.application.medical_chat import MedicalChatApplication
from app.modules.qa.application.records import MedicalChatRequestRecord, MedicalChatResult
from app.modules.qa.domain.safety import fallback_reply, is_emergency
from app.modules.reports.application.ports import ReportDraftCommand
from app.modules.reports.application.use_cases import ReportsApplication
from app.modules.reports.domain.policy import ReportPolicy
from app.modules.training.domain.state import (
    CASE_STAGES,
    AssessmentCandidate,
    TrainingPolicy,
    apply_ai_candidates,
    deterministic_assessment,
    summarize_dimensions,
)
from app.shared.actor import Actor
from app.shared.errors import AppError


def _actor(*, role: str = "student", actor_id: int = 7) -> Actor:
    return Actor(actor_id, f"user-{actor_id}", role, "测试用户")


def test_training_stage_policy_and_deterministic_assessment_are_transport_free() -> None:
    assert CASE_STAGES == ("history", "problem_representation", "differential", "tests", "management")
    assert TrainingPolicy.next_stage("history") == "problem_representation"
    assert TrainingPolicy.next_stage("management") is None

    with pytest.raises(AppError, match="当前阶段不可提交"):
        TrainingPolicy.require_in_progress("history", "tests")

    rubric = {
        "dimensions": [
            {
                "id": dimension_id,
                "label": dimension_id,
                "weight": weight,
                "stage_ids": stages,
                "criteria": [{"keywords": [dimension_id], "feedback": "补充证据。"}],
            }
            for dimension_id, _label, weight, stages in (
                ("information_gathering", "信息采集", 20, ["history"]),
                ("problem_representation", "问题表征", 15, ["problem_representation"]),
                ("differential_diagnosis", "鉴别诊断", 20, ["differential"]),
                ("evidence_reasoning", "证据推理", 15, ["differential"]),
                ("test_selection", "检查合理性", 15, ["tests"]),
                ("management_safety", "处置与安全意识", 15, ["management"]),
            )
        ]
    }
    attempt = SimpleNamespace(
        problem=SimpleNamespace(rubric=rubric),
        messages=(SimpleNamespace(role="user", content="information_gathering"),),
        submissions=(),
    )
    dimensions, focus_stage, _strengths, weaknesses, _next_steps, total, _notice = deterministic_assessment(attempt)
    assert dimensions[0]["score"] == 100.0
    assert focus_stage == "problem_representation"
    assert "problem_representation" in weaknesses
    assert total == 20


def test_ai_candidates_cannot_change_deterministic_scores_or_evidence() -> None:
    rubric = {
        "dimensions": [
            {
                "id": dimension_id,
                "label": dimension_id,
                "weight": weight,
                "stage_ids": stages,
                "criteria": [{"keywords": [dimension_id], "feedback": "补充证据。"}],
            }
            for dimension_id, _label, weight, stages in (
                ("information_gathering", "信息采集", 20, ["history"]),
                ("problem_representation", "问题表征", 15, ["problem_representation"]),
                ("differential_diagnosis", "鉴别诊断", 20, ["differential"]),
                ("evidence_reasoning", "证据推理", 15, ["differential"]),
                ("test_selection", "检查合理性", 15, ["tests"]),
                ("management_safety", "处置与安全意识", 15, ["management"]),
            )
        ]
    }
    empty_attempt = SimpleNamespace(
        problem=SimpleNamespace(rubric=rubric),
        messages=(),
        submissions=(),
    )
    dimensions, *_rest, deterministic_total, _notice = deterministic_assessment(empty_attempt)
    before = [
        (item["dimension_id"], item["score"], item["weighted_score"], list(item["evidence"])) for item in dimensions
    ]

    candidates = (
        AssessmentCandidate("information_gathering", 100000, (), "高分反馈", "高分下一步"),
        AssessmentCandidate("problem_representation", -100, (), "负分反馈", "负分下一步"),
        AssessmentCandidate("differential_diagnosis", 100, (), "空证据反馈", "空证据下一步"),
        AssessmentCandidate("evidence_reasoning", 100, ("伪造的学生原文",), "伪造反馈", "伪造下一步"),
    )
    apply_ai_candidates(empty_attempt, dimensions, candidates)

    after = [
        (item["dimension_id"], item["score"], item["weighted_score"], list(item["evidence"])) for item in dimensions
    ]
    assert deterministic_total == 0
    assert after == before
    assert dimensions[0]["feedback"] == "高分反馈"
    assert dimensions[1]["feedback"] == "负分反馈"
    assert dimensions[2]["feedback"] == "空证据反馈"
    assert dimensions[3]["feedback"] != "伪造反馈"
    _focus, _strengths, _weaknesses, _next_steps, total_after = summarize_dimensions(dimensions)
    assert total_after == deterministic_total


def test_ai_candidate_with_valid_student_evidence_still_cannot_change_score() -> None:
    rubric = {
        "dimensions": [
            {
                "id": dimension_id,
                "label": dimension_id,
                "weight": weight,
                "stage_ids": stages,
                "criteria": [{"keywords": [dimension_id], "feedback": "补充证据。"}],
            }
            for dimension_id, _label, weight, stages in (
                ("information_gathering", "信息采集", 20, ["history"]),
                ("problem_representation", "问题表征", 15, ["problem_representation"]),
                ("differential_diagnosis", "鉴别诊断", 20, ["differential"]),
                ("evidence_reasoning", "证据推理", 15, ["differential"]),
                ("test_selection", "检查合理性", 15, ["tests"]),
                ("management_safety", "处置与安全意识", 15, ["management"]),
            )
        ]
    }
    attempt = SimpleNamespace(
        problem=SimpleNamespace(rubric=rubric),
        messages=(SimpleNamespace(role="user", content="information_gathering"),),
        submissions=(),
    )
    dimensions, *_rest, deterministic_total, _notice = deterministic_assessment(attempt)
    before = [(item["score"], item["weighted_score"], list(item["evidence"])) for item in dimensions]

    apply_ai_candidates(
        attempt,
        dimensions,
        (AssessmentCandidate("information_gathering", 1, ("information_gathering",), "可信反馈", "可信下一步"),),
    )

    after = [(item["score"], item["weighted_score"], list(item["evidence"])) for item in dimensions]
    assert after == before
    assert dimensions[0]["feedback"] == "可信反馈"
    _focus, _strengths, _weaknesses, _next_steps, total_after = summarize_dimensions(dimensions)
    assert total_after == deterministic_total == 20


def test_content_and_report_policies_reject_unsafe_transitions_and_scope() -> None:
    with pytest.raises(AppError) as content_error:
        ContentPolicy.require_publishable_case({}, {})
    assert (content_error.value.code, content_error.value.status_code) == ("VALIDATION_ERROR", 422)

    assert ContentPolicy.is_visible_to_student(
        status="published",
        target="class",
        target_ids=("class-a",),
        student_external_id="student-1",
        class_codes={"class-a"},
    )
    assert not ContentPolicy.is_visible_to_student(
        status="draft",
        target="all",
        target_ids=(),
        student_external_id="student-1",
        class_codes=set(),
    )

    policy = ReportPolicy()
    assert policy.can_read(_actor(), 7, "draft")
    assert not policy.can_read(_actor(role="teacher", actor_id=2), 7, "draft")
    with pytest.raises(AppError, match="报告状态不允许"):
        policy.require_transition("draft", "reviewed")


def test_application_use_cases_recheck_resource_ownership_without_http() -> None:
    class ReportRepository:
        def conversation_owner(self, _conversation_id: int) -> int:
            return 7

    class ContentRepository:
        def get(self, _problem_id: int):
            return SimpleNamespace(content_type="guided_case", author_id=7)

    class Uow:
        def commit(self) -> None:
            raise AssertionError("an unauthorized use case must not commit")

        def rollback(self) -> None:
            raise AssertionError("an ownership rejection needs no persistence rollback")

    student_application = ReportsApplication(ReportRepository(), Uow())
    with pytest.raises(AppError) as report_error:
        student_application.save_draft(
            _actor(actor_id=99), ReportDraftCommand(conversation_id=12, ai_score=80, ai_summary="x", analysis=None)
        )
    assert (report_error.value.code, report_error.value.status_code) == ("RESOURCE_NOT_FOUND", 404)

    content_application = ContentApplication(ContentRepository(), Uow())
    with pytest.raises(AppError) as content_error:
        content_application.authoring(_actor(role="teacher", actor_id=99), 12)
    assert (content_error.value.code, content_error.value.status_code) == ("RESOURCE_NOT_FOUND", 404)


def test_learning_micro_scoring_is_bounded_and_targets_weakest_dimensions() -> None:
    score, evidence, feedback, next_step = assess_micro(
        {"answer": "病史和检查"},
        {
            "criteria": [
                {"keywords": ["病史"], "weight": 60, "feedback": "继续补充病史。"},
                {"keywords": ["鉴别"], "weight": 40, "feedback": "补充鉴别。", "critical": True},
            ]
        },
    )
    assert score == 60.0
    assert evidence == ["病史和检查"]
    assert feedback == "补充鉴别。"
    assert next_step == "补充缺失证据后再次练习。"
    assert target_dimensions(
        (
            {"dimension_id": "problem_representation", "score": 40},
            {"dimension_id": "information_gathering", "score": 50},
            {"dimension_id": "test_selection", "score": 90},
        )
    ) == ["problem_representation", "information_gathering"]


def test_qa_safety_policy_is_deterministic_without_external_clients() -> None:
    emergency = "患者突然呼吸困难，喘不上气"
    assert is_emergency(emergency)
    assert "120" in fallback_reply(emergency, None)
    assert not is_emergency("请解释鉴别诊断的教学方法")
    assert "演示反馈" in fallback_reply("请解释鉴别诊断的教学方法", "病例分析")


def test_medical_chat_audit_failure_rolls_back_and_maps_to_application_error() -> None:
    class Gateway:
        def reply(self, _request: MedicalChatRequestRecord) -> MedicalChatResult:
            return MedicalChatResult("教学反馈", True, "disabled", "fallback", "test-v1", 1)

    class Audit:
        def record_ai_call(self, **_kwargs: object) -> None:
            raise RuntimeError("simulated audit outage")

    class Uow:
        def __init__(self) -> None:
            self.rollbacks = 0

        def commit(self) -> None:
            raise AssertionError("audit failure must prevent commit")

        def rollback(self) -> None:
            self.rollbacks += 1

    uow = Uow()
    application = MedicalChatApplication(Gateway(), Audit(), uow)
    with pytest.raises(AppError, match="AI audit") as error:
        application.reply(_actor(), MedicalChatRequestRecord("问题", None, ()))
    assert (error.value.code, error.value.status_code, uow.rollbacks) == ("SERVICE_ERROR", 503, 1)
