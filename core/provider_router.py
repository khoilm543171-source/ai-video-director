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
    """OpenAI-compatible LLM facade with retry and failover."""

    def __init__(
        self,
        clients: list[OpenAICompatibleLLM],
        route_name: str,
    ):
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
        self.default_provider = (
            os.getenv("LLM_PROVIDER", "vilao").lower().strip()
        )
        self.fallback_provider = (
            os.getenv("LLM_FALLBACK_PROVIDER", "").lower().strip()
        )

    def _configs(self, provider: str) -> list[ProviderConfig]:
        provider = provider.lower().strip()

        if provider == "vilao":
            key = os.getenv("VILAO_API_KEY", "").strip()
            model = os.getenv("VILAO_MODEL", "").strip()

            if not key:
                raise LLMConfigurationError(
                    "VILAO_API_KEY is missing in .env."
                )

            if not model:
                raise LLMConfigurationError(
                    "VILAO_MODEL is missing in .env."
                )

            fallback_models = [
                item.strip()
                for item in os.getenv(
                    "VILAO_FALLBACK_MODELS",
                    "",
                ).split(",")
                if item.strip()
            ]

            models = [model]
            for fallback_model in fallback_models:
                if fallback_model not in models:
                    models.append(fallback_model)

            base_url = os.getenv(
                "VILAO_BASE_URL",
                "https://api.vilao.ai/v1",
            ).rstrip("/")

            return [
                ProviderConfig(
                    name="vilao",
                    base_url=base_url,
                    api_key=key,
                    model=model_id,
                )
                for model_id in models
            ]

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

            return [
                ProviderConfig(
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
            ]

        if provider in {"generic", "openai_compatible"}:
            key = os.getenv("LLM_API_KEY", "").strip()
            model = os.getenv("LLM_MODEL", "").strip()
            base_url = os.getenv("LLM_BASE_URL", "").strip()

            if not key or not model or not base_url:
                raise LLMConfigurationError(
                    "Generic provider requires LLM_BASE_URL, "
                    "LLM_MODEL, and LLM_API_KEY."
                )

            return [
                ProviderConfig(
                    name="generic",
                    base_url=base_url.rstrip("/"),
                    api_key=key,
                    model=model,
                )
            ]

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

        provider_names = [primary_name]

        if (
            self.fallback_provider
            and self.fallback_provider != primary_name
        ):
            provider_names.append(self.fallback_provider)

        configs: list[ProviderConfig] = []

        for provider_name in provider_names:
            configs.extend(self._configs(provider_name))

        clients = [
            self._client(config)
            for config in configs
        ]

        route_name = " -> ".join(
            f"{config.name}:{config.model}"
            for config in configs
        )

        return RoutedLLM(
            clients=clients,
            route_name=route_name,
        )
