from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"
VENDOR = ROOT / "vendor"
SUPPORTED = {"vilao", "deepseek", "generic", "openai_compatible"}


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

    if provider not in SUPPORTED:
        problems.append(
            f"Unknown LLM_PROVIDER={provider}; use vilao, deepseek, or generic"
        )

    if fallback and fallback not in SUPPORTED:
        problems.append(
            f"Unknown LLM_FALLBACK_PROVIDER={fallback}; "
            "use vilao, deepseek, generic, or leave it blank"
        )

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
            shown = (
                masked(os.getenv(name))
                if name.endswith("KEY")
                else os.getenv(name) or "MISSING"
            )
            print(f"{name:13}: {shown}")
            if not os.getenv(name):
                problems.append(f"Add {name} to .env")

    if fallback == "deepseek" and provider != "deepseek":
        print(f"Fallback key : {masked(os.getenv('DEEPSEEK_API_KEY'))}")
        if not os.getenv("DEEPSEEK_API_KEY"):
            problems.append(
                "DeepSeek fallback is enabled but DEEPSEEK_API_KEY is missing. "
                "Either add the key or set LLM_FALLBACK_PROVIDER="
            )

    print(f"vendor/      : {yesno(VENDOR.exists())}")
    for name in ("chatterbox", "mmaudio", "ace-step", "kokoro-fastapi"):
        path = VENDOR / name
        print(f"  {name:16}: {yesno(path.exists())}")

    print("\nAudio config (not required for planning-only episode test):")
    print(
        "  MMAUDIO_ROOT   : "
        + os.getenv("MMAUDIO_ROOT", "vendor/mmaudio")
    )
    print(
        "  ACESTEP_URL    : "
        + os.getenv("ACESTEP_URL", "http://127.0.0.1:8001")
    )
    print(
        "  ACESTEP_API_KEY: "
        + ("SET" if os.getenv("ACESTEP_API_KEY") else "blank (local auth off)")
    )

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
    print("Later, before audio rendering: python scripts/audio_doctor.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
