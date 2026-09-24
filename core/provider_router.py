from __future__ import annotations

import os
import time
from dataclasses import dataclass

from core.llm_client import (
    LLMConfigurationError,
    LLMTransientError,
    OpenAICompatibleLLM,
)


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    base_url: str
    api_key: str
    model: str


class RoutedLLM:
    """OpenAI-compatible LLM facade with retry + provider failover."""

    def __init__(self, clients: list[OpenAICompatibleLLM], route_name: str):
        if not clients:
            raise LLMConfigurationError("No LLM clients configured.")
        self.clients = clients
        self.route_name = route_name
        self.active = clients[0]
        self.last_usage: dict[str, int] = {}
        self.retry_attempts = max(
            1,
            int(os.getenv("LLM_RETRY_ATTEMPTS", "2")),
        )
        self.retry_backoff = max(
            0.0,
            float(os.getenv("LLM_RETRY_BACKOFF_SECONDS", "1.5")),
        )

    @property
    def model(self) -> str:
        return self.route_name

    @property
    def base_url(self) -> str:
        return " -> ".join(client.base_url for client in self.clients)

    def chat_json(self, *args, **kwargs):
        errors: list[str] = []

        for client in self.clients:
            for attempt in range(1, self.retry_attempts + 1):
                try:
                    result = client.chat_json(*args, **kwargs)
                    self.active = client
                    self.last_usage = client.last_usage
                    return result
                except LLMTransientError as exc:
                    errors.append(
                        f"{client.base_url} / {client.model} "
                        f"(attempt {attempt}/{self.retry_attempts}): "
                        f"{type(exc).__name__}: {exc}"
                    )
                    if attempt < self.retry_attempts:
                        time.sleep(
                            self.retry_backoff * (2 ** (attempt - 1))
                        )
                        continue
                    break
                except Exception as exc:
                    errors.append(
                        f"{client.base_url} / {client.model}: "
                        f"{type(exc).__name__}: {exc}"
                    )
                    break

        raise RuntimeError(
            "All configured LLM providers failed:\n- "
            + "\n- ".join(errors)
        )


class ProviderRouter:
    STAGES = {
        "idea",
        "story",
        "script",
        "storyboard",
        "veo_prompt_builder",
        "audio_director",
    }

    def __init__(self):
        self.default_provider = os.getenv("LLM_PROVIDER", "vilao").lower()
        self.fallback_provider = (
            os.getenv("LLM_FALLBACK_PROVIDER", "").lower().strip()
        )

    def _configs(self, provider: str) -> list[ProviderConfig]:
        provider = provider.lower()

        if provider == "vilao":
            key = os.getenv("VILAO_API_KEY", "").strip()
            model = os.getenv("VILAO_MODEL", "").strip()
            if not key:
                raise LLMConfigurationError(
                    "VILAO_API_KEY is missing in .env."
                )
            if not model:
                raise LLMConfigurationError(
                    "VILAO_MODEL is missing in .env. Copy the exact model ID "
                    "shown in your Vilao Marketplace/API example."
                )

            fallback_models = [
                item.strip()
                for item in os.getenv("VILAO_FALLBACK_MODELS", "").split(",")
                if item.strip()
            ]