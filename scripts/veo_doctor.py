from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"
load_dotenv(ENV, override=False)


def hidden(value: str | None) -> str:
    return "OK (hidden)" if value else "MISSING"


def main() -> int:
    problems: list[str] = []

    print(f"Project root : {ROOT}")
    print(f"Python       : {sys.executable}")

    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    model = os.getenv("VEO_MODEL", "veo-3.1-generate-preview")
    ratio = os.getenv("VEO_ASPECT_RATIO", "9:16")
    resolution = os.getenv("VEO_RESOLUTION", "") or "provider default"
    duration = (
        os.getenv("VEO_FORCE_DURATION_SECONDS", "")
        or "scene duration from veo_prompts.json"
    )

    print(f"Gemini key   : {hidden(key)}")
    print(f"Veo model    : {model}")
    print(f"Aspect ratio : {ratio}")
    print(f"Resolution   : {resolution}")
    print(f"Duration     : {duration}")

    try:
        import google.genai  # noqa: F401
        print("google-genai : OK")
    except ImportError:
        print("google-genai : MISSING")
        problems.append(
            "Install dependencies: pip install -r requirements-orchestrator.txt"
        )

    if not key:
        problems.append(
            "Add GEMINI_API_KEY (or GOOGLE_API_KEY) to .env. "
            "A Gemini app subscription alone is not an API credential."
        )

    if not model.strip():
        problems.append("VEO_MODEL is empty.")

    if problems:
        print("\nFix:")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print("\nVeo configuration looks ready.")
    print("First run a dry-run against one existing episode:")
    print(
        "python scripts/render_episode.py "
        "--episode-id YOUR_EPISODE_ID --scene scene_01 --dry-run"
    )
    print("Then remove --dry-run to generate exactly one video scene.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
