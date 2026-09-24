from __future__ import annotations

import json
from typing import Any, TypeVar

from pydantic import BaseModel

from core.llm_client import OpenAICompatibleLLM


T = TypeVar("T", bound=BaseModel)


def run_typed_agent(
    llm: OpenAICompatibleLLM,
    output_model: type[T],
    *,
    system_prompt: str,
    payload: dict[str, Any],
    temperature: float = 0.3,
    max_tokens: int = 6000,
) -> T:
    schema = output_model.model_json_schema()

    user_prompt = (
        "INPUT DATA:\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + "\n\nREQUIRED OUTPUT JSON SCHEMA:\n"
        + json.dumps(schema, ensure_ascii=False, indent=2)
        + "\n\nReturn one JSON object only. Do not use Markdown."
    )

    raw = llm.chat_json(
        system_prompt,
        user_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return output_model.model_validate(raw)
