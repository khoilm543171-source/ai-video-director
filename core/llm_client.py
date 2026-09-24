from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=False)


class LLMConfigurationError(RuntimeError):
    pass


class LLMResponseError(RuntimeError):
    pass


class LLMTransientError(LLMResponseError):
    """Retryable provider/upstream failure."""


class OpenAICompatibleLLM:
    """Minimal OpenAI-compatible client for JSON-first agents."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_s: int = 120,
    ):
        self.base_url = (
            base_url
            or os.getenv("LLM_BASE_URL")
            or "https://api.deepseek.com"
        ).rstrip("/")
        self.api_key = (
            api_key
            or os.getenv("LLM_API_KEY")
            or os.getenv("DEEPSEEK_API_KEY")
        )
        self.model = model or os.getenv("LLM_MODEL") or "deepseek-chat"
        self.timeout_s = timeout_s
        self.last_usage: dict[str, int] = {}
        self.total_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

        if not self.api_key:
            if not ENV_PATH.exists():
                hint = (
                    f"No .env file found at {ENV_PATH}. "
                    "Run: Copy-Item .env.example .env, then add LLM_API_KEY."
                )
            else:
                hint = (
                    f".env exists at {ENV_PATH}, but the selected provider "
                    "API key is empty or missing."
                )
            raise LLMConfigurationError(hint)

    def chat(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.4,
        max_tokens: int = 6000,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout_s,
            )
        except (requests.Timeout, requests.ConnectionError) as exc:
            raise LLMTransientError(
                f"Temporary network error calling {self.base_url}: {exc}"
            ) from exc

        if response.status_code == 429 or response.status_code >= 500:
            raise LLMTransientError(
                f"LLM temporary HTTP error ({response.status_code}): "
                f"{response.text[:1200]}"
            )

        if response.status_code >= 400:
            raise LLMResponseError(
                f"LLM request failed ({response.status_code}): "
                f"{response.text[:1200]}"
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise LLMTransientError(
                f"Provider returned non-JSON response: {response.text[:1200]}"
            ) from exc

        if isinstance(body, dict) and body.get("error"):
            error = body["error"]
            message = (
                error.get("message")
                if isinstance(error, dict)
                else str(error)
            ) or "Unknown provider error"
            error_type = (
                error.get("type", "")
                if isinstance(error, dict)
                else ""
            )
            lowered = f"{message} {error_type}".lower()

            transient_markers = (
                "temporarily",
                "temporary",
                "upstream",
                "overloaded",
                "timeout",
                "timed out",
                "rate limit",
                "rate_limit",
                "unavailable",
                "server error",
                "api_error",
            )

            exc_type = (
                LLMTransientError
                if any(marker in lowered for marker in transient_markers)
                else LLMResponseError
            )
            raise exc_type(
                f"Provider error: {message}"
                + (f" (type={error_type})" if error_type else "")
            )

        usage = body.get("usage") or {}
        self.last_usage = {
            "prompt_tokens": int(usage.get("prompt_tokens") or 0),
            "completion_tokens": int(usage.get("completion_tokens") or 0),
            "total_tokens": int(usage.get("total_tokens") or 0),
        }
        for key in self.total_usage:
            self.total_usage[key] += self.last_usage[key]

        try:
            choice = body["choices"][0]
            content = choice["message"]["content"]
            finish_reason = choice.get("finish_reason")
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMResponseError(
                f"Unexpected LLM response shape: {body}"
            ) from exc

        if finish_reason == "length":
            raise LLMTransientError(
                f"LLM output truncated at max_tokens={max_tokens}."
            )

        return content

    def chat_json(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.3,
        max_tokens: int = 6000,
    ) -> dict[str, Any]:
        text = self.chat(
            system,
            user,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return extract_json_object(text)


def extract_json_object(text: str) -> dict[str, Any]:
    candidate = text.strip()
    fence = chr(96) * 3

    if candidate.startswith(fence):
        candidate = re.sub(
            r"^" + re.escape(fence) + r"(?:json)?\s*",
            "",
            candidate,
            flags=re.I,
        )
        candidate = re.sub(
            r"\s*" + re.escape(fence) + r"$",
            "",
            candidate,
        )

    try:
        value = json.loads(candidate)
        if not isinstance(value, dict):
            raise LLMResponseError("LLM JSON output must be an object.")
        return value
    except json.JSONDecodeError:
        pass

    start = candidate.find("{")
    end = candidate.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise LLMResponseError(
            f"Could not find JSON object in LLM output: {text[:1200]}"
        )

    try:
        value = json.loads(candidate[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMResponseError(
            f"Invalid JSON returned by LLM: {text[:1200]}"
        ) from exc

    if not isinstance(value, dict):
        raise LLMResponseError("LLM JSON output must be an object.")

    return value