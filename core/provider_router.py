from __future__ import annotations

import os
from dataclasses import dataclass

from core.llm_client import (
    LLMConfigurationError,
    OpenAICompatibleLLM,
)


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    base_url: str
    api_key: str
    model: str


class RoutedLLM:
    """OpenAI-compatible LLM facade with provider failover."""

    def __init__(self, clients: list[OpenAICompatibleLLM], route_name: str):
        if not clients:
            raise LLMConfigurationError("No LLM clients configured.")
        self.clients = clients
        self.route_name = route_name
        self.active = clients[0]
        self.last_usage: dict[str, int] = {}

    @property
    def model(self) -> str:
        return self.route_name

    @property
    def base_url(self) -> str:
        return " -> ".join(client.base_url for client in self.clients)

    def chat_json(self, *args, **kwargs):
        errors: list[str] = []

        for client in self.clients:
            try:
                result = client.chat_json(*args, **kwargs)
                self.active = client
                self.last_usage = client.last_usage
                return result
            except Exception as exc:
                errors.append(
                    f"{client.base_url} / {client.model}: "
                    f"{type(exc).__name__}: {exc}"
                )

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
            os.getenv("LLM_FALLBACK_PROVIDER", "deepseek").lower().strip()
        )

    def _config(self, provider: str) -> ProviderConfig:
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
            return ProviderConfig(
                name="vilao",
                base_url=os.getenv(
                    "VILAO_BASE_URL",
                    "https://api.vilao.ai/v1",
                ).rstrip("/"),
                api_key=key,
                model=model,
            )

        if provider == "deepseek":
            key = (
                os.getenv("DEEPSEEK_API_KEY")
                or os.getenv("LLM_API_KEY")
                or ""
            ).strip()
            if not key:
                raise LLMConfigurationError(
                    "DEEPSEEK_API_KEY is missing in .env."
                )
            return ProviderConfig(
                name="deepseek",
                base_url=os.getenv(
                    "DEEPSEEK_BASE_URL",
                    "https://api.deepseek.com",
                ).rstrip("/"),
                api_key=key,
                model=os.getenv(
                    "DEEPSEEK_MODEL",
                    "deepseek-chat",
                ).strip(),
            )

        if provider in {"generic", "openai_compatible"}:
            key = os.getenv("LLM_API_KEY", "").strip()
            model = os.getenv("LLM_MODEL", "").strip()
            base_url = os.getenv("LLM_BASE_URL", "").strip()
            if not key or not model or not base_url:
                raise LLMConfigurationError(
                    "Generic provider requires LLM_BASE_URL, LLM_MODEL, "
                    "and LLM_API_KEY."
                )
            return ProviderConfig(
                name="generic",
                base_url=base_url.rstrip("/"),
                api_key=key,
                model=model,
            )

        raise LLMConfigurationError(
            f"Unknown LLM provider: {provider}. "
            "Supported: vilao, deepseek, generic."
        )

    @staticmethod
    def _client(config: ProviderConfig) -> OpenAICompatibleLLM:
        return OpenAICompatibleLLM(
            base_url=config.base_url,
            api_key=config.api_key,
            model=config.model,
        )

    def for_stage(self, stage: str) -> RoutedLLM:
        if stage not in self.STAGES:
            raise ValueError(f"Unknown LLM stage: {stage}")

        env_name = f"{stage.upper()}_LLM_PROVIDER"
        primary_name = os.getenv(
            env_name,
            self.default_provider,
        ).lower().strip()

        names = [primary_name]
        if (
            self.fallback_provider
            and self.fallback_provider != primary_name
        ):
            names.append(self.fallback_provider)

        configs = [self._config(name) for name in names]
        clients = [self._client(config) for config in configs]
        route_name = " -> ".join(
            f"{config.name}:{config.model}"
            for config in configs
        )

        return RoutedLLM(clients, route_name=route_name)
