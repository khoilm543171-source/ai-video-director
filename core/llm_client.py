from __future__ import annotations

import json
import os
import re
from typing import Any

import requests


class LLMConfigurationError(RuntimeError):
    pass


class LLMResponseError(RuntimeError):
    pass


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

        if not self.api_key:
            raise LLMConfigurationError(
                "Missing LLM API key. Set LLM_API_KEY or DEEPSEEK_API_KEY."
            )

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

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.timeout_s,
        )

        if response.status_code >= 400:
            raise LLMResponseError(
                f"LLM request failed ({response.status_code}): "
                f"{response.text[:1200]}"
            )

        body = response.json()

        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMResponseError(
                f"Unexpected LLM response shape: {body}"
            ) from exc

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
