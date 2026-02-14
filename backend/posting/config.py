from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# Get the directory containing this config file
CONFIG_DIR = Path(__file__).parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(CONFIG_DIR / ".env"),
        env_file_encoding="utf-8",
    )

    database_url: str = f"sqlite+aiosqlite:///{CONFIG_DIR}/posting.db"
    upload_dir: Path = CONFIG_DIR / "uploads"

    browserbase_api_key: str = ""
    browserbase_project_id: str = ""
    browserbase_context_id: str = ""  # Context ID with Facebook logged in
    model_api_key: str = ""  # OpenAI API key for Stagehand AI

    worker_poll_interval: int = 5
    max_retries: int = 3


settings = Settings()
