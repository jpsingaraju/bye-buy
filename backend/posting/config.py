from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    upload_dir: Path = Path(__file__).parent / "uploads"

    browserbase_api_key: str = ""
    browserbase_project_id: str = ""
    browserbase_context_id: str = ""
    model_api_key: str = ""

    craigslist_location: str = ""
    craigslist_zip_code: str = ""
    craigslist_email: str = ""

    worker_poll_interval: int = 5
    max_retries: int = 3


settings = Settings()
