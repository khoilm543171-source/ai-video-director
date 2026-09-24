from __future__ import annotations

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"
load_dotenv(ENV, override=False)


def resolve_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def main() -> int:
    problems: list[str] = []

    mmaudio_root = resolve_path(
        os.getenv("MMAUDIO_ROOT", "vendor/mmaudio")
    )
    demo = mmaudio_root / "demo.py"

    print(f"MMAudio root : {mmaudio_root}")
    print(f"MMAudio demo : {'OK' if demo.exists() else 'MISSING'}")

    if not demo.exists():
        problems.append(
            "MMAudio demo.py was not found. Check MMAUDIO_ROOT."
        )

    ace_url = os.getenv(
        "ACESTEP_URL",
        "http://127.0.0.1:8001",
    ).rstrip("/")
    ace_key = os.getenv("ACESTEP_API_KEY", "").strip()

    print(f"ACE-Step URL : {ace_url}")
    print(
        "ACE-Step key : "
        + ("SET (hidden)" if ace_key else "blank (allowed for local auth-off mode)")
    )

    headers = {}
    if ace_key:
        headers["Authorization"] = f"Bearer {ace_key}"

    try:
        response = requests.get(
            f"{ace_url}/health",
            headers=headers,
            timeout=3,
        )
        if response.ok:
            print("ACE-Step API : OK")
        else:
            print(f"ACE-Step API : HTTP {response.status_code}")
            problems.append(
                "ACE-Step responded but health check was not OK."
            )
    except requests.RequestException:
        print("ACE-Step API : NOT RUNNING / UNREACHABLE")
        print(
            "This is fine until the music-render stage. "
            "Start ACE-Step before generating background music."
        )

    if problems:
        print("\nFix:")
        for item in problems:
            print(f"- {item}")
        return 1

    print("\nAudio configuration looks usable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
