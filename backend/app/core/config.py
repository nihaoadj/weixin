from functools import lru_cache

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
    pbl_ai_provider: str = "coze"
    pbl_ai_timeout_seconds: int = 12
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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def demo_auth_enabled(self) -> bool:
        return self.enable_demo_auth and not self.is_production

    @property
    def wechat_teacher_openid_list(self) -> set[str]:
        return {item.strip() for item in self.wechat_teacher_openids.split(",") if item.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
