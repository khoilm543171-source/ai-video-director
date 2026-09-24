from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel


DROP_SCHEMA_KEYS = {"title", "description", "examples", "default"}


def compact_json_schema(value: Any) -> Any:
    """Remove verbose JSON-schema metadata while preserving validation shape."""
    if isinstance(value, dict):
        return {
            key: compact_json_schema(item)
            for key, item in value.items()
            if key not in DROP_SCHEMA_KEYS
        }
    if isinstance(value, list):
        return [compact_json_schema(item) for item in value]
    return value


def compact_dumps(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def rough_token_estimate(text: str) -> int:
    # Conservative language-agnostic estimate used only for local budget warnings.
    return max(1, (len(text) + 3) // 4)


def stable_hash(*parts: str) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(part.encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()


class LLMCache:
    def __init__(self, root: str | Path | None = None):
        self.enabled = os.getenv("LLM_CACHE", "true").lower() not in {
            "0",
            "false",
            "no",
        }
        self.root = Path(
            root
            or os.getenv("LLM_CACHE_DIR")
            or ".cache/llm"
        )

    def get(self, key: str) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        path = self.root / f"{key}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def set(self, key: str, payload: dict[str, Any]) -> None:
        if not self.enabled:
            return
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{key}.json"
        path.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )


def write_usage_event(event: dict[str, Any]) -> None:
    path = Path(
        os.getenv("LLM_USAGE_LOG")
        or "outputs/token_usage.jsonl"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(event, ensure_ascii=False, separators=(",", ":"))
            + "\n"
        )


def minimal_character_visuals(character_bible: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in character_bible.get("characters", {}).items():
        out[key] = {
            "display_name": value.get("display_name"),
            "role": value.get("role"),
            "visual_identity": value.get("visual_identity", {}),
        }
    return out


def minimal_character_voices(character_bible: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value.get("voice_direction")
        for key, value in character_bible.get("characters", {}).items()
    }


def minimal_series_visuals(series_bible: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "aspect_ratio",
        "target_resolution",
        "visual_style",
        "story_rule",
        "teaching_rule",
        "continuity_rules",
    )
    return {
        key: series_bible[key]
        for key in keys
        if key in series_bible
    }


def model_payload(model: BaseModel, include: set[str] | None = None) -> dict[str, Any]:
    data = model.model_dump()
    if include is None:
        return data
    return {key: data[key] for key in include if key in data}
