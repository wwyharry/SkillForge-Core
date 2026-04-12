from __future__ import annotations

import json
import ssl
from typing import Any
from urllib import error, parse, request

from app.schemas.model_config import ModelApiConfig


class ModelApiClient:
    def __init__(self, config: ModelApiConfig) -> None:
        self.config = config

    def is_ready(self) -> bool:
        if not self.config.enabled or not self.config.api_key or not self.config.base_url:
            return False
        if self._provider_family() == "azure-openai":
            return bool(self.config.deployment_name)
        return bool(self.config.model_name)

    def embedding_ready(self) -> bool:
        if not self.config.enabled or not self.config.api_key or not self.config.base_url:
            return False
        return bool(self.config.embedding_model or self.config.model_name or self.config.deployment_name)

    def test_connection(self) -> dict[str, Any]:
        if not self.config.base_url:
            return {"ok": False, "message": "API base URL is required."}
        if not self.config.api_key:
            return {"ok": False, "message": "API key is required."}

        models: list[str] = []
        model_error = ""
        try:
            payload = self._get_models_payload()
            models = self._extract_model_ids(payload)
            return {
                "ok": True,
                "message": f"Connection succeeded: the models endpoint is reachable. Current provider: {self.config.provider}. Discovered {len(models)} model(s) or endpoint(s).",
                "models": models[:20],
            }
        except Exception as exc:
            model_error = self._error_message(exc)

        try:
            self._chat_probe()
            configured = [item for item in [self.config.model_name, self.config.deployment_name] if item]
            return {
                "ok": True,
                "message": (
                    "Connection succeeded: the chat endpoint is reachable, but the models endpoint is unavailable. "
                    "This usually means the current service supports OpenAI-compatible chat calls but does not expose a standard /models endpoint. "
                    f"This usually does not affect chat or generation. Models endpoint error: {model_error}"
                ),
                "models": configured[:20],
            }
        except Exception as exc:
            chat_error = self._error_message(exc)
            return {
                "ok": False,
                "message": (
                    f"Connection failed: the models endpoint is unavailable ({model_error}), and the chat probe also failed ({chat_error})."
                ),
                "models": [],
            }

    def chat(self, system_prompt: str, user_prompt: str, temperature: float | None = None, max_tokens: int | None = None) -> str:
        if not self.is_ready():
            raise RuntimeError("Model API is not fully configured.")

        payload = self._chat_payload(system_prompt, user_prompt, temperature, max_tokens)
        response_payload = self._post_json(self._chat_url(), payload)
        return self._extract_chat_content(response_payload)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not self.embedding_ready():
            raise RuntimeError("Embedding API is not fully configured.")
        payload = self._embedding_payload(texts)
        response_payload = self._post_json(self._embedding_url(), payload)

        items = response_payload.get("data", [])
        if not isinstance(items, list):
            raise RuntimeError("Embedding response did not contain data array.")
        vectors: list[list[float]] = []
        for item in items:
            embedding = item.get("embedding") if isinstance(item, dict) else None
            if isinstance(embedding, list):
                vectors.append([float(value) for value in embedding])
        return vectors

    def _chat_probe(self) -> str:
        if not self.is_ready():
            raise RuntimeError("Model API is not fully configured for chat probing.")
        return self.chat(
            system_prompt="Reply with exactly: pong",
            user_prompt="ping",
            temperature=0.0,
            max_tokens=8,
        )

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        req = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={**self._headers(), "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.config.timeout_seconds, context=self._ssl_context()) as response:
                return json.loads(response.read().decode("utf-8") or "{}")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HTTP {exc.code}: {detail or exc.reason}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Connection failed: {exc.reason}") from exc

    def _get_models_payload(self) -> dict[str, Any]:
        req = request.Request(self._models_url(), headers=self._headers(), method="GET")
        with request.urlopen(req, timeout=self.config.timeout_seconds, context=self._ssl_context()) as response:
            return json.loads(response.read().decode("utf-8") or "{}")

    def _error_message(self, exc: Exception) -> str:
        if isinstance(exc, error.HTTPError):
            detail = exc.read().decode("utf-8", errors="ignore")
            return f"HTTP {exc.code}: {detail or exc.reason}"
        if isinstance(exc, error.URLError):
            return f"Connection failed: {exc.reason}"
        return str(exc)

    def _provider_family(self) -> str:
        provider = self.config.provider.strip().lower() or "openai-compatible"
        if provider in {"openai", "openai-compatible", "openrouter", "deepseek", "custom"}:
            return "openai-compatible"
        if provider == "azure-openai":
            return "azure-openai"
        if provider in {"anthropic", "anthropic-compatible"}:
            return "anthropic-compatible"
        return "openai-compatible"

    def _models_url(self) -> str:
        family = self._provider_family()
        if family == "azure-openai":
            return self._join_url(f"openai/models?api-version={self._api_version()}")
        if family == "anthropic-compatible":
            return self._join_url("models")
        return self._join_url("models")

    def _chat_url(self) -> str:
        family = self._provider_family()
        if family == "azure-openai":
            deployment = self.config.deployment_name.strip()
            return self._join_url(f"openai/deployments/{deployment}/chat/completions?api-version={self._api_version()}")
        if family == "anthropic-compatible":
            return self._join_url("messages")
        return self._join_url("chat/completions")

    def _embedding_url(self) -> str:
        family = self._provider_family()
        if family == "azure-openai":
            deployment = (self.config.embedding_model or self.config.deployment_name).strip()
            return self._join_url(f"openai/deployments/{deployment}/embeddings?api-version={self._api_version()}")
        return self._join_url("embeddings")

    def _chat_payload(self, system_prompt: str, user_prompt: str, temperature: float | None, max_tokens: int | None) -> dict[str, Any]:
        family = self._provider_family()
        chosen_temperature = self.config.temperature if temperature is None else temperature
        chosen_max_tokens = self.config.max_tokens if max_tokens is None else max_tokens
        if family == "anthropic-compatible":
            return {
                "model": self.config.model_name,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
                "temperature": chosen_temperature,
                "top_p": self.config.top_p,
                "max_tokens": chosen_max_tokens,
                "stream": False,
            }
        payload: dict[str, Any] = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": chosen_temperature,
            "top_p": self.config.top_p,
            "max_tokens": chosen_max_tokens,
            "stream": False,
        }
        if family != "azure-openai":
            payload["model"] = self.config.model_name
        return payload

    def _embedding_payload(self, texts: list[str]) -> dict[str, Any]:
        family = self._provider_family()
        if family == "azure-openai":
            return {"input": texts}
        return {
            "model": self.config.embedding_model or self.config.model_name,
            "input": texts,
        }

    def _extract_chat_content(self, response_payload: dict[str, Any]) -> str:
        family = self._provider_family()
        if family == "anthropic-compatible":
            content = response_payload.get("content", [])
            if isinstance(content, list):
                text = "\n".join(item.get("text", "") for item in content if isinstance(item, dict))
                if text.strip():
                    return text.strip()
            raise RuntimeError("No content returned by Anthropic-compatible API.")

        choices = response_payload.get("choices", [])
        if not choices:
            raise RuntimeError("No choices returned by model API.")
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):
            return "\n".join(part.get("text", "") for part in content if isinstance(part, dict)).strip()
        return str(content).strip()

    def _extract_model_ids(self, payload: dict[str, Any]) -> list[str]:
        family = self._provider_family()
        if family == "azure-openai":
            items = payload.get("data", []) if isinstance(payload, dict) else []
            return [item.get("id", "") for item in items if isinstance(item, dict) and item.get("id")]
        items = payload.get("data", []) if isinstance(payload, dict) else []
        if items:
            return [item.get("id", "") for item in items if isinstance(item, dict) and item.get("id")]
        if self.config.model_name:
            return [self.config.model_name]
        if self.config.deployment_name:
            return [self.config.deployment_name]
        return []

    def _join_url(self, path: str) -> str:
        base = self.config.base_url.strip()
        if not base:
            return path
        if not base.endswith("/"):
            base += "/"
        return parse.urljoin(base, path)

    def _api_version(self) -> str:
        return self.config.api_version.strip() or "2024-10-21"

    def _headers(self) -> dict[str, str]:
        family = self._provider_family()
        headers = {"Accept": "application/json"}
        if family == "azure-openai":
            headers["api-key"] = self.config.api_key
        elif family == "anthropic-compatible":
            headers["x-api-key"] = self.config.api_key
            headers["anthropic-version"] = self.config.api_version.strip() or "2023-06-01"
        else:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        if self.config.organization:
            headers["OpenAI-Organization"] = self.config.organization
        if self.config.project:
            headers["OpenAI-Project"] = self.config.project
        for item in self.config.extra_headers:
            if item.name.strip():
                headers[item.name.strip()] = item.value
        return headers

    def _ssl_context(self) -> ssl.SSLContext | None:
        if self.config.verify_ssl:
            return None
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context
