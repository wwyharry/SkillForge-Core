from __future__ import annotations

from pydantic import BaseModel

from app.schemas.model_config import ModelApiConfig


class ModelApiTestRequest(BaseModel):
    config: ModelApiConfig


class ModelApiTestResult(BaseModel):
    ok: bool
    message: str
    models: list[str] = []
