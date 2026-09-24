from __future__ import annotations

from functools import lru_cache
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = PROJECT_ROOT / ".opencode" / "skills"


@lru_cache(maxsize=32)
def load_skill(name: str) -> str:
    path = SKILL_ROOT / name / "SKILL.md"
    if not path.exists():
        raise FileNotFoundError(f"Skill not found: {path}")

    text = path.read_text(encoding="utf-8").strip()

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            text = parts[2].strip()

    return text


def compose_skills(*names: str) -> str:
    blocks = [load_skill(name) for name in names]
    return "\n\n".join(blocks)
