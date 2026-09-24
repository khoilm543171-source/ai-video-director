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


def masked(value: str | None) -> str:
    return "OK (hidden)" if value else "MISSING"


def main() -> int:
    print(f"Project root : {ROOT}")
    print(f"Python       : {sys.executable}")
    print(f".env         : {yesno(ENV.exists())} ({ENV})")

    if ENV.exists():
        load_dotenv(ENV, override=False)

    provider = os.getenv("LLM_PROVIDER", "vilao").lower().strip()
    fallback = os.getenv("LLM_FALLBACK_PROVIDER", "").lower().strip()

    print(f"LLM provider : {provider}")
    print(f"Fallback     : {fallback or 'disabled'}")

    problems: list[str] = []

    if provider == "vilao":
        print(
            "Vilao URL    : "
            + os.getenv("VILAO_BASE_URL", "https://api.vilao.ai/v1")
        )
        print(f"Vilao key    : {masked(os.getenv('VILAO_API_KEY'))}")
        print(f"Vilao model  : {os.getenv('VILAO_MODEL') or 'MISSING'}")
        if not os.getenv("VILAO_API_KEY"):
            problems.append("Add VILAO_API_KEY to .env")
        if not os.getenv("VILAO_MODEL"):
            problems.append(
                "Add the exact Vilao model ID to VILAO_MODEL"
            )

    elif provider == "deepseek":
        print(
            "DeepSeek URL : "
            + os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        )
        print(f"DeepSeek key : {masked(os.getenv('DEEPSEEK_API_KEY'))}")
        print(
            "DeepSeek mdl : "
            + os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        )
        if not os.getenv("DEEPSEEK_API_KEY"):
            problems.append("Add DEEPSEEK_API_KEY to .env")

    elif provider in {"generic", "openai_compatible"}:
        for name in ("LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY"):
            print(f"{name:13}: {masked(os.getenv(name)) if name.endswith('KEY') else os.getenv(name) or 'MISSING'}")
            if not os.getenv(name):
                problems.append(f"Add {name} to .env")
    else:
        problems.append(
            f"Unknown LLM_PROVIDER={provider}; use vilao, deepseek, or generic"
        )

    if fallback == "deepseek" and provider != "deepseek":
        print(
            f"Fallback key : {masked(os.getenv('DEEPSEEK_API_KEY'))}"
        )
        if not os.getenv("DEEPSEEK_API_KEY"):
            print(
                "NOTE         : DeepSeek fallback is configured but has no key; "
                "set LLM_FALLBACK_PROVIDER= to disable fallback."
            )

    print(f"vendor/      : {yesno(VENDOR.exists())}")
    for name in ("chatterbox", "mmaudio", "ace-step", "kokoro-fastapi"):
        path = VENDOR / name
        print(f"  {name:16}: {yesno(path.exists())}")

    if not ENV.exists():
        problems.append("Create .env from .env.example")

    if problems:
        print("\nFix:")
        for item in problems:
            print(f"- {item}")
        return 1

    print("\nCore configuration looks ready.")
    print("Next: python scripts/test_llm.py")
    print("Then: python -m pytest -q tests")
    print("Then: python scripts/run_episode.py --input examples/episode_request.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())