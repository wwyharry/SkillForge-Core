from __future__ import annotations

import json
from pathlib import Path

from app.core.config import settings
from app.schemas.model_config import ModelApiConfig


class ModelConfigService:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or settings.data_dir / "model_api_config.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def get(self) -> ModelApiConfig:
        if not self.path.exists():
            return ModelApiConfig(
                provider="openai-compatible",
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key,
                model_name=settings.llm_model_name,
                embedding_model=settings.llm_embedding_model,
                deployment_name=settings.llm_deployment_name,
                api_version=settings.llm_api_version,
                organization=settings.llm_organization,
                project=settings.llm_project,
                timeout_seconds=settings.llm_timeout_seconds,
                max_tokens=settings.llm_max_tokens,
                temperature=settings.llm_temperature,
                top_p=settings.llm_top_p,
                enabled=settings.llm_enabled,
                verify_ssl=settings.llm_verify_ssl,
                use_streaming=settings.llm_use_streaming,
            )

        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return ModelApiConfig.model_validate(payload)

    def save(self, config: ModelApiConfig) -> ModelApiConfig:
        self.path.write_text(config.model_dump_json(indent=2), encoding="utf-8")
        return config

    def masked(self) -> dict:
        config = self.get()
        data = config.model_dump()
        api_key = data.get("api_key", "")
        if api_key:
            data["api_key_masked"] = f"{api_key[:6]}...{api_key[-4:]}" if len(api_key) > 10 else "********"
            data["api_key"] = ""
        else:
            data["api_key_masked"] = ""
        return data
