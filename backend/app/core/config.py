import os
from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./data/dev.db"
    jwt_secret: str = "change-me-in-local-env"
    access_token_expire_minutes: int = 60 * 24 * 7
    cors_origins: str = "http://localhost:5173,http://localhost:5174"
    enable_demo_auth: bool = True
    ai_enabled: bool = False
    ai_base_url: str = ""
    ai_api_key: str = ""
    ai_model: str = ""
    ai_timeout_seconds: int = 12
    ai_prompt_version: str = "case-v2"
    pbl_ai_enabled: bool = False
    pbl_mock_enabled: bool = False
    pbl_ai_provider: str = "openai_compatible"
    pbl_ai_timeout_seconds: int = 25
    pbl_ai_prompt_version: str = "pathology-pbl-v1"
    coze_api_base: str = ""
    coze_api_token: str = ""
    coze_invocation_mode: str = ""
    coze_bot_id: str = ""
    coze_workflow_id: str = ""
    coze_app_id: str = ""
    pbl_openai_base_url: str = ""
    pbl_openai_api_key: str = ""
    pbl_openai_model: str = ""
    practice_prompt_version: str = "practice-v1"
    seed_showcase_case: bool = True
    # T08 switches stop new learning evidence while preserving existing records for rollback.
    t08_learning_context_enabled: bool = True
    t08_exit_quiz_enabled: bool = True
    t08_review_capture_enabled: bool = True
    wechat_app_id: str = ""
    wechat_app_secret: str = ""
    wechat_api_base_url: str = "https://api.weixin.qq.com"
    wechat_teacher_openids: str = ""

    model_config = SettingsConfigDict(env_file=None, env_file_encoding="utf-8")

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def demo_auth_enabled(self) -> bool:
        return self.enable_demo_auth and not self.is_production

    @model_validator(mode="after")
    def validate_pbl_provider_contract(self) -> "Settings":
        provider = self.pbl_ai_provider.strip().lower()
        if self.pbl_mock_enabled:
            if self.app_env.strip().lower() != "test":
                raise ValueError("PBL_MOCK_ENABLED 仅允许测试环境")
            return self
        if self.is_production and provider != "coze":
            raise ValueError("生产环境 PBL 必须使用 Coze")
        if not self.pbl_ai_enabled:
            return self
        if provider not in {"coze", "openai_compatible"}:
            raise ValueError("PBL_AI_PROVIDER 无效")
        if provider == "openai_compatible":
            if not all((self.pbl_openai_base_url, self.pbl_openai_api_key, self.pbl_openai_model)):
                raise ValueError("PBL 普通 API 配置不完整")
            return self
        if not self.coze_api_token or self.coze_invocation_mode not in {"bot", "workflow"}:
            raise ValueError("Coze PBL 配置不完整")
        if self.coze_invocation_mode == "bot" and not self.coze_bot_id:
            raise ValueError("COZE_BOT_ID 必填")
        if self.coze_invocation_mode == "workflow":
            resource_ids = [item for item in (self.coze_app_id, self.coze_bot_id) if item]
            if not self.coze_workflow_id or len(resource_ids) != 1:
                raise ValueError("Workflow 资源配置不完整")
        return self

    @property
    def wechat_teacher_openid_list(self) -> set[str]:
        return {item.strip() for item in self.wechat_teacher_openids.split(",") if item.strip()}


@lru_cache
def get_settings() -> Settings:
    controlled = os.environ.get("APP_ENV", "").strip().lower() in {"test", "contract-export"}
    env_file = None if controlled else Path(__file__).resolve().parents[2] / ".env"
    return Settings(_env_file=env_file)
