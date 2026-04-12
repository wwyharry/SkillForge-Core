from __future__ import annotations

from pydantic import BaseModel, Field


class ModelApiConfig(BaseModel):
    provider: str = "openai-compatible"
    base_url: str = ""
    api_key: str = ""
    model_name: str = ""
    embedding_model: str = ""
    deployment_name: str = ""
    api_version: str = ""
    organization: str = ""
    project: str = ""
    timeout_seconds: int = 120
    max_tokens: int = 4096
    temperature: float = 0.2
    top_p: float = 1.0
    enabled: bool = False
    verify_ssl: bool = True
    use_streaming: bool = False
    notes: str = ""
    extra_headers: list[dict[str, str]] = Field(default_factory=list)


class ModelApiConfigForm(BaseModel):
    provider: str = "openai-compatible"
    base_url: str = ""
    api_key: str = ""
    model_name: str = ""
    embedding_model: str = ""
    deployment_name: str = ""
    api_version: str = ""
    organization: str = ""
    project: str = ""
    timeout_seconds: int = 120
    max_tokens: int = 4096
    temperature: float = 0.2
    top_p: float = 1.0
    enabled: bool = False
    verify_ssl: bool = True
    use_streaming: bool = False
    notes: str = ""
    extra_header_names: list[str] = Field(default_factory=list)
    extra_header_values: list[str] = Field(default_factory=list)

    def to_config(self) -> ModelApiConfig:
        headers: list[dict[str, str]] = []
        for name, value in zip(self.extra_header_names, self.extra_header_values):
            key = name.strip()
            header_value = value.strip()
            if key:
                headers.append({"name": key, "value": header_value})
        return ModelApiConfig(
            provider=self.provider.strip() or "openai-compatible",
            base_url=self.base_url.strip(),
            api_key=self.api_key.strip(),
            model_name=self.model_name.strip(),
            embedding_model=self.embedding_model.strip(),
            deployment_name=self.deployment_name.strip(),
            api_version=self.api_version.strip(),
            organization=self.organization.strip(),
            project=self.project.strip(),
            timeout_seconds=max(1, self.timeout_seconds),
            max_tokens=max(1, self.max_tokens),
            temperature=min(max(self.temperature, 0.0), 2.0),
            top_p=min(max(self.top_p, 0.0), 1.0),
            enabled=self.enabled,
            verify_ssl=self.verify_ssl,
            use_streaming=self.use_streaming,
            notes=self.notes.strip(),
            extra_headers=headers,
        )
