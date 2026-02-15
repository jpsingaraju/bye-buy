from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    gpt_model: str = "gpt-5.2"

    poll_interval_min: int = 3
    poll_interval_max: int = 8
    response_delay_min: int = 5
    response_delay_max: int = 15
    max_conversations_per_cycle: int = 5
    full_sweep_interval: int = 10
    session_break_cycles: int = 75
    session_break_min: int = 60
    session_break_max: int = 120

    browserbase_api_key: str = ""
    browserbase_project_id: str = ""
    browserbase_context_id: str = ""
    model_api_key: str = ""

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_connected_account_id: str = ""


settings = Settings()
