from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=False)

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.skill_loader import load_skill


def main() -> int:
    problems: list[str] = []

    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    model = os.getenv("VISUAL_REVIEW_MODEL", "gemini-2.5-flash")

    print(f"Project root       : {ROOT}")
    print(f"Gemini key         : {'OK (hidden)' if key else 'MISSING'}")
    print(f"Visual review model: {model}")

    try:
        import google.genai  # noqa: F401
        print("google-genai       : OK")
    except ImportError:
        print("google-genai       : MISSING")
        problems.append(
            "Run: pip install -r requirements-orchestrator.txt"
        )

    try:
        skill = load_skill("visual-review")
        print(f"visual-review skill: OK ({len(skill)} chars)")
    except Exception as exc:
        print(f"visual-review skill: FAIL ({exc})")
        problems.append("Pull the latest repo so visual-review skill exists.")

    if not key:
        problems.append(
            "Add GEMINI_API_KEY from Google AI Studio to .env."
        )

    if problems:
        print("\nFix:")
        for item in problems:
            print(f"- {item}")
        return 1

    print("\nVisual Reviewer is configured.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
