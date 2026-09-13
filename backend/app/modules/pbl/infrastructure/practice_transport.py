"""Coze-only JSON transport for unreviewed private practice."""

import json

from app.core.config import Settings
from app.modules.pbl.infrastructure.providers.coze_client import build_coze_client
from app.modules.pbl.infrastructure.providers.coze_events import completed_stream_text


class PracticeTransport:
    def __init__(self, settings: Settings):
        self._settings = settings

    def practice_json(self, context: dict, schema: dict) -> str:
        if self._settings.pbl_mock_enabled or self._settings.app_env.strip().lower() == "test":
            if self._settings.app_env.strip().lower() != "test":
                raise RuntimeError("PBL 本地 Mock 仅允许测试环境")
            return json.dumps(self._mock(context), ensure_ascii=False)
        if not self._settings.pbl_ai_enabled or self._settings.pbl_ai_provider != "coze":
            raise RuntimeError("未配置 Coze 未审核练习服务")
        if self._settings.coze_invocation_mode not in {"bot", "workflow"} or not self._settings.coze_api_token:
            raise RuntimeError("Coze 未审核练习配置不完整")
        client = build_coze_client(self._settings.coze_api_token, self._settings.coze_api_base)
        prompt = self._prompt(context, schema)
        if self._settings.coze_invocation_mode == "bot":
            if not self._settings.coze_bot_id:
                raise RuntimeError("COZE_BOT_ID 必填")
            events = client.chat.stream(
                bot_id=self._settings.coze_bot_id,
                user_id="pbl-private-practice",
                additional_messages=[{"role": "user", "content": prompt, "content_type": "text"}],
            )
        else:
            resource_ids = [item for item in (self._settings.coze_app_id, self._settings.coze_bot_id) if item]
            if not self._settings.coze_workflow_id or len(resource_ids) != 1:
                raise RuntimeError("Workflow 资源配置不完整")
            resource_kind = "app_id" if self._settings.coze_app_id else "bot_id"
            events = client.workflows.chat.stream(
                workflow_id=self._settings.coze_workflow_id,
                additional_messages=[{"role": "user", "content": prompt, "content_type": "text"}],
                **{resource_kind: resource_ids[0]},
            )
        text, _ = completed_stream_text(events)
        return text

    @staticmethod
    def _prompt(context: dict, schema: dict) -> str:
        material = context["material"]
        safe_findings = [
            {key: item.get(key) for key in ("id", "point_code", "summary", "dimension_id", "improvement")}
            for item in context.get("findings", [])
        ]
        return json.dumps(
            {
                "instruction": "Create at most three private pathology single-choice practice questions. "
                "They are unreviewed AI practice; do not diagnose or prescribe. Return only JSON matching schema.",
                "schema": schema,
                "point_code": context["point_code"],
                "cycle": context["cycle"],
                "public_material": {key: material[key] for key in ("title", "objective", "scenario", "remediation")},
                "findings": safe_findings,
            },
            ensure_ascii=False,
        )

    @staticmethod
    def _mock(context: dict) -> dict:
        material = context["material"]
        options = ["用机制和可观察证据共同解释", "只背诵结论", "忽略证据限制", "把相关性当作因果"]
        if context["cycle"] == 2:
            options = ["先说明证据，再比较机制", "只重复第一次结论", "不核对情境线索", "把不确定性当成错误"]
        return {
            "schema_version": 1,
            "safety_status": "educational",
            "questions": [
                {
                    "point_code": context["point_code"],
                    "prompt": f"未审核 AI 练习：{material['scenario']}",
                    "options": options,
                    "reference_option": 0,
                    "explanation": "按 AI 参考答案，应把机制解释与可核对的形态或情境证据联系起来。",
                }
            ],
        }
