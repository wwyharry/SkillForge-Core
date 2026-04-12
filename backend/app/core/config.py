from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SkillForge API"
    app_version: str = "0.3.0"
    data_dir: Path = Path("data")
    export_dir: Path = Path("exports")
    cors_origins: list[str] = ["http://localhost:8000"]
    database_url: str = "postgresql+psycopg://skillforge:skillforge@localhost:5432/skillforge"
    redis_url: str = "redis://localhost:6379/0"
    use_async_pipeline: bool = False
    use_database_persistence: bool = False
    broker_url: str | None = None
    result_backend: str | None = None
    api_base_url: str = "http://localhost:8000"
    llm_enabled: bool = False
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model_name: str = ""
    llm_embedding_model: str = ""
    llm_deployment_name: str = ""
    llm_api_version: str = ""
    llm_organization: str = ""
    llm_project: str = ""
    llm_timeout_seconds: int = 120
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.2
    llm_top_p: float = 1.0
    llm_verify_ssl: bool = True
    llm_use_streaming: bool = False
    parser_extensions: list[str] = Field(default_factory=lambda: [".md", ".txt", ".docx", ".pdf", ".xlsx"])

    model_config = SettingsConfigDict(env_prefix="SKILLFORGE_", env_file=".env")


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.export_dir.mkdir(parents=True, exist_ok=True)
