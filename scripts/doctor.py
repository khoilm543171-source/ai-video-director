from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"
VENDOR = ROOT / "vendor"


def yesno(value: bool) -> str:
    return "OK" if value else "MISSING"


def main() -> int:
    print(f"Project root : {ROOT}")
    print(f"Python       : {sys.executable}")
    print(f".env         : {yesno(ENV.exists())} ({ENV})")

    if ENV.exists():
        load_dotenv(ENV, override=False)

    key = os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    print(f"LLM API key  : {'OK (hidden)' if key else 'MISSING'}")
    print(f"LLM base URL : {os.getenv('LLM_BASE_URL') or 'https://api.deepseek.com'}")
    print(f"LLM model    : {os.getenv('LLM_MODEL') or 'deepseek-chat'}")

    print(f"vendor/      : {yesno(VENDOR.exists())}")
    for name in ("chatterbox", "mmaudio", "ace-step", "kokoro-fastapi"):
        path = VENDOR / name
        print(f"  {name:16}: {yesno(path.exists())}")

    problems = []
    if not ENV.exists():
        problems.append("Create .env from .env.example")
    if not key:
        problems.append("Add LLM_API_KEY or DEEPSEEK_API_KEY to .env")

    if problems:
        print("\nFix:")
        for item in problems:
            print(f"- {item}")
        return 1

    print("\nCore configuration looks ready.")
    print("Next: pytest -q")
    print("Then: python scripts/run_episode.py --input examples/episode_request.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
