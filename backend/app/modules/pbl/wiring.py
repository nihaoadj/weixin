from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.pbl.application.records import InferenceRequest, InferenceResult
from app.modules.pbl.application.use_cases import PblApplication
from app.modules.pbl.infrastructure.providers import CozeBotGateway, CozeWorkflowGateway, OpenAICompatibleGateway


class DisabledGateway:
    def infer(self, request: InferenceRequest) -> InferenceResult:
        return InferenceResult("PBL 教学助手当前未启用。", "unavailable", failure_reason="disabled")


def _gateway():
    s = get_settings()
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
    from cozepy import Coze, TokenAuth

    client = Coze(auth=TokenAuth(token=s.coze_api_token), base_url=s.coze_api_base or None)
    if s.coze_invocation_mode == "bot":
        if not s.coze_bot_id:
            raise RuntimeError("COZE_BOT_ID 必填")
        return CozeBotGateway(client, s.coze_bot_id, s.pbl_ai_prompt_version), "coze", "bot"
    if not s.coze_workflow_id or not (s.coze_app_id or s.coze_bot_id):
        raise RuntimeError("Workflow 资源配置不完整")
    return (
        CozeWorkflowGateway(client, s.coze_workflow_id, s.coze_bot_id or s.coze_app_id, s.pbl_ai_prompt_version),
        "coze",
        "workflow",
    )


def pbl_application(session: Session) -> PblApplication:
    gateway, provider, mode = _gateway()
    return PblApplication(session, gateway, provider, mode)
