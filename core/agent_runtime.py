from __future__ import annotations

import os
from typing import Any, TypeVar

from pydantic import BaseModel

from core.llm_client import OpenAICompatibleLLM
from core.token_economy import (
    LLMCache,
    compact_dumps,
    compact_json_schema,
    rough_token_estimate,
    stable_hash,
    write_usage_event,
)


T = TypeVar("T", bound=BaseModel)


def run_typed_agent(
    llm: OpenAICompatibleLLM,
    output_model: type[T],
    *,
    system_prompt: str,
    payload: dict[str, Any],
    temperature: float = 0.3,
    max_tokens: int = 4000,
    agent_name: str | None = None,
) -> T:
    name = agent_name or output_model.__name__
    schema = compact_json_schema(output_model.model_json_schema())

    user_prompt = (
        "INPUT:"
        + compact_dumps(payload)
        + "\nOUTPUT_SCHEMA:"
        + compact_dumps(schema)
        + "\nJSON only."
    )

    estimated_input_tokens = rough_token_estimate(system_prompt + user_prompt)
    soft_budget = int(os.getenv("LLM_PROMPT_TOKEN_BUDGET", "6000"))

    if estimated_input_tokens > soft_budget:
        raise ValueError(
            f"{name} prompt estimate {estimated_input_tokens} tokens exceeds "
            f"LLM_PROMPT_TOKEN_BUDGET={soft_budget}. Reduce context instead of "
            "sending a larger window."
        )

    cache = LLMCache()
    cache_key = stable_hash(
        llm.model,
        name,
        system_prompt,
        user_prompt,
        str(temperature),
    )
    cached = cache.get(cache_key)

    if cached is not None:
        write_usage_event(
            {
                "agent": name,
                "cache_hit": True,
                "prompt_estimate_tokens": estimated_input_tokens,
                "provider_prompt_tokens": 0,
                "provider_completion_tokens": 0,
                "provider_total_tokens": 0,
            }
        )
        return output_model.model_validate(cached)

    raw = llm.chat_json(
        system_prompt,
        user_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    validated = output_model.model_validate(raw)
    cache.set(cache_key, validated.model_dump())

    usage = llm.last_usage or {}
    write_usage_event(
        {
            "agent": name,
            "cache_hit": False,
            "prompt_estimate_tokens": estimated_input_tokens,
            "provider_prompt_tokens": int(usage.get("prompt_tokens") or 0),
            "provider_completion_tokens": int(usage.get("completion_tokens") or 0),
            "provider_total_tokens": int(usage.get("total_tokens") or 0),
        }
    )

    return validated
