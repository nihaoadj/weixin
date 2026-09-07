from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.classroom.wiring import classroom_scope_port
from app.modules.content.wiring import question_publication_port
from app.modules.learning.wiring import pbl_learning_port
from app.modules.pbl.application.records import InferenceRequest, InferenceResult
from app.modules.pbl.application.use_cases import PblApplication
from app.modules.pbl.infrastructure.checked_gateway import CheckedGateway
from app.modules.pbl.infrastructure.providers import CozeBotGateway, CozeWorkflowGateway, OpenAICompatibleGateway
from app.modules.pbl.infrastructure.providers.coze_client import build_coze_client
from app.modules.pbl.infrastructure.repositories import SqlAlchemyPblRepository


class DisabledGateway:
    def infer(self, request: InferenceRequest) -> InferenceResult:
        return InferenceResult(
            "PBL 教学助手当前未启用。",
            "unavailable",
            failure_reason="disabled",
            interaction_style=request.interaction_style,
        )


class LocalMockGateway:
    """Deterministic test-only provider used by the API-mode local E2E suite."""

    def infer(self, request: InferenceRequest) -> InferenceResult:
        phase_prompts = {
            "problem_framing": "请用一句话概括当前病理问题，并指出关键形态线索。",
            "hypothesis": "请提出至少一个机制假设，并说明你最不确定的地方。",
            "evidence": "哪些病例证据支持或反驳该假设？这些证据有什么限制？",
        }
        if request.current_phase != "synthesis":
            reply = phase_prompts[request.current_phase]
            if request.interaction_style == "direct":
                reply = f"先说明：{request.question}需要结合当前病理主题与阶段证据判断。理解检验：{reply}"
            return InferenceResult(
                reply,
                "probing",
                follow_up_question=phase_prompts[request.current_phase],
                provider_metadata={"provider": "local_mock", "mode": "test"},
                phase_assessment={
                    "phase": request.current_phase,
                    "decision": "advance",
                    "evidence_message_ids": [request.message_id],
                    "evidence_summary": "合成测试回答满足当前阶段目标。",
                    "missing_elements": [],
                },
                interaction_style=request.interaction_style,
            )
        return InferenceResult(
            "你已经开始联系血管反应与炎症表现，但还需要区分不同机制。",
            "ready",
            knowledge_gaps=(
                {
                    "id": "gap-1",
                    "point_code": request.goal_point_codes[0]
                    if request.goal_point_codes
                    else "pathology.inflammation.vascular",
                    "summary": "机制解释需要补充",
                    "confidence": "medium",
                    "evidence_message_ids": [request.message_id],
                    "evidence_summary": "学生的第二次解释尚未区分相关机制。",
                },
            ),
            reasoning_issues=(
                {
                    "id": "reason-1",
                    "dimension_id": "evidence_reasoning",
                    "issue_type": "missing_evidence",
                    "summary": "结论与组织学依据连接不足",
                    "evidence_message_ids": [request.message_id],
                    "evidence_summary": "解释未明确指出支持结论的形态证据。",
                    "improvement": "先列出观察，再说明推断。",
                },
            ),
            recommended_questions=(
                {
                    "title": "炎症早期的血管反应",
                    "prompt": "请用血流变化和通透性变化解释红、肿、热。",
                    "objective": "区分观察与推断",
                    "linked_findings": ["gap-1", "reason-1"],
                },
            ),
            provider_metadata={"provider": "local_mock", "mode": "test"},
            phase_assessment={
                "phase": "synthesis",
                "decision": "complete",
                "evidence_message_ids": [request.message_id],
                "evidence_summary": "合成测试回答完成机制、证据与疑问整合。",
                "missing_elements": [],
            },
            interaction_style=request.interaction_style,
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
    gateway, provider, mode = _gateway()
    return PblApplication(
        SqlAlchemyPblRepository(session),
        session,
        CheckedGateway(gateway),
        classroom_scope_port(session),
        question_publication_port(session),
        provider,
        mode,
        pbl_learning_port(session),
    )
