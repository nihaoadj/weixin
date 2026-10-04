from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.classroom.wiring import classroom_scope_port
from app.modules.content.wiring import knowledge_catalog_port, question_publication_port
from app.modules.pbl.application.records import (
    InferenceRequest,
    InferenceResult,
    LearningResponseRecord,
    PrivateFollowupRequest,
    PrivateFollowupResult,
)
from app.modules.pbl.application.use_cases import PblApplication
from app.modules.pbl.infrastructure.checked_gateway import CheckedGateway
from app.modules.pbl.infrastructure.classroom_participation import SqlPblClassroomParticipation
from app.modules.pbl.infrastructure.providers import CozeBotGateway, CozeWorkflowGateway, OpenAICompatibleGateway
from app.modules.pbl.infrastructure.providers.coze_client import build_coze_client
from app.modules.pbl.infrastructure.providers.coze_parser import unavailable_private_follow_up, unavailable_result
from app.modules.pbl.infrastructure.providers.response_renderer import render_learning_response
from app.modules.pbl.infrastructure.repositories import SqlAlchemyPblRepository


def pbl_classroom_participation_port(session: Session) -> SqlPblClassroomParticipation:
    return SqlPblClassroomParticipation(session)


def pbl_student_insight_read_port(session: Session):
    return SqlAlchemyPblRepository(session)


class DisabledGateway:
    def infer(self, request: InferenceRequest) -> InferenceResult:
        return unavailable_result("disabled", request.interaction_style)

    def private_follow_up(self, request: PrivateFollowupRequest) -> PrivateFollowupResult:
        return unavailable_private_follow_up("disabled", request.interaction_style)


class LocalMockGateway:
    """Deterministic test-only provider used by the API-mode local E2E suite."""

    def infer(self, request: InferenceRequest) -> InferenceResult:
        if request.schema_version != 8:
            return unavailable_result("retired_schema", request.interaction_style)
        return self._infer_v8(request)

    def _infer_v8(self, request: InferenceRequest) -> InferenceResult:
        complete = request.current_phase == "synthesis"
        sections = LearningResponseRecord(
            "合成教学演示：整理观察、机制与证据之间的联系。",
            ("请区分可见病理变化与推断，并说明证据限制。",),
            "研讨已完成，学习计划正在生成。" if complete else "请继续解释本阶段的病理依据。",
        )
        no_gaps = "无明确薄弱点" in request.question or not request.goal_point_codes
        gaps = (
            (
                {
                    "id": "gap-1",
                    "point_code": request.goal_point_codes[0],
                    "summary": "机制解释需要补充",
                    "confidence": "medium",
                    "evidence_message_ids": [request.message_id],
                    "evidence_summary": "合成教学回答的机制证据连接需要完善。",
                },
            )
            if complete and not no_gaps
            else ()
        )
        return InferenceResult(
            render_learning_response(sections),
            "ready" if complete else "probing",
            response_sections=sections,
            schema_version=8,
            interaction_style=request.interaction_style,
            diagnosis_outcome=("no_clear_gaps" if no_gaps else "identified_gaps") if complete else None,
            knowledge_gaps=gaps,
            provider_metadata={"provider": "local_mock", "mode": "test"},
            phase_assessment={
                "phase": request.current_phase,
                "decision": "complete" if complete else "advance",
                "evidence_message_ids": [request.message_id],
                "evidence_summary": "合成回答满足当前教学阶段目标。",
                "missing_elements": [],
            },
        )

    def private_follow_up(self, request: PrivateFollowupRequest) -> PrivateFollowupResult:
        opening = (
            "先直接说明：炎症表现需要把局部血流变化、血管通透性和渗出联系起来。"
            if request.interaction_style == "direct"
            else "你可以先比较血流增加与血管通透性增加分别解释了哪些表现。"
        )
        sections = LearningResponseRecord(
            opening,
            ("这是完成后的合成私人问答，不会改变已冻结证据。", "AI 回复不作为正式学习证据。"),
            "尝试用一条形态观察和一条机制依据重新表述你的理解。",
        )
        return PrivateFollowupResult(
            assistant_reply=render_learning_response(sections),
            interaction_style=request.interaction_style,
            provider_metadata={"provider": "local_mock", "mode": "test"},
            safety_notice="Demo 合成教学演示，不能替代临床诊疗。",
            response_sections=sections,
        )


def _gateway():
    s = get_settings()
    if s.pbl_mock_enabled:
        if s.app_env.strip().lower() != "test":
            raise RuntimeError("PBL 本地 Mock 仅允许测试环境")
        return LocalMockGateway(), "local_mock", "test"
    if not s.pbl_ai_enabled:
        return DisabledGateway(), "disabled", None
    if s.pbl_ai_provider not in {"coze", "openai_compatible"}:
        raise RuntimeError("PBL_AI_PROVIDER 无效")
    if s.is_production and s.pbl_ai_provider != "coze":
        raise RuntimeError("生产环境 PBL 必须使用 Coze")
    if s.pbl_ai_provider == "openai_compatible":
        if not all((s.pbl_openai_base_url, s.pbl_openai_api_key, s.pbl_openai_model)):
            raise RuntimeError("PBL 普通 API 配置不完整")
        return (
            OpenAICompatibleGateway(
                s.pbl_openai_base_url,
                s.pbl_openai_api_key,
                s.pbl_openai_model,
                s.pbl_ai_timeout_seconds,
                s.pbl_ai_prompt_version,
            ),
            "openai_compatible",
            None,
        )
    if not s.coze_api_token or s.coze_invocation_mode not in {"bot", "workflow"}:
        raise RuntimeError("Coze PBL 配置不完整")
    client = build_coze_client(s.coze_api_token, s.coze_api_base)
    if s.coze_invocation_mode == "bot":
        if not s.coze_bot_id:
            raise RuntimeError("COZE_BOT_ID 必填")
        return CozeBotGateway(client, s.coze_bot_id, s.pbl_ai_prompt_version), "coze", "bot"
    resource_ids = [item for item in (s.coze_app_id, s.coze_bot_id) if item]
    if not s.coze_workflow_id or len(resource_ids) != 1:
        raise RuntimeError("Workflow 资源配置不完整")
    return (
        CozeWorkflowGateway(
            client,
            s.coze_workflow_id,
            resource_ids[0],
            "app" if s.coze_app_id else "bot",
            s.pbl_ai_prompt_version,
        ),
        "coze",
        "workflow",
    )


def pbl_application(session: Session) -> PblApplication:
    from app.modules.learning.wiring import learning_evidence_port, learning_route_application

    gateway, provider, mode = _gateway()
    return PblApplication(
        SqlAlchemyPblRepository(session, classroom_scope_port(session)),
        session,
        CheckedGateway(gateway),
        classroom_scope_port(session),
        question_publication_port(session),
        provider,
        mode,
        knowledge_catalog_port(session),
        learning_evidence_port(session),
        completion_routes=learning_route_application(session),
    )


def study_dialogue_port(session: Session):
    from app.modules.pbl.infrastructure.study_dialogues import StudyDialogues

    return StudyDialogues(pbl_application(session), SqlAlchemyPblRepository(session, classroom_scope_port(session)))


def practice_json_port():
    from app.modules.pbl.infrastructure.practice_transport import PracticeTransport

    return PracticeTransport(get_settings())


def learning_route_inference_port():
    gateway, _, _ = _gateway()
    return CheckedGateway(gateway)


def pbl_teacher_diagnosis_read_port(session: Session):
    return SqlAlchemyPblRepository(session, classroom_scope_port(session))
