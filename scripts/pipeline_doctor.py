from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=False)

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.skill_loader import load_skill


SKILLS = [
    "episode-orchestration",
    "content-review",
    "camera-direction",
    "flow-video-prompt",
    "visual-review",
    "voice-direction",
    "sfx-foley",
    "music-direction",
]


def yes_no(value: bool) -> str:
    return "OK" if value else "MISSING"


def main() -> int:
    hard_failures: list[str] = []
    optional: list[str] = []

    print("=== AI Video Director Pipeline Doctor ===")
    print(f"Root   : {ROOT}")
    print(f"Python : {sys.executable}")
    print()

    print("[Skills]")
    for name in SKILLS:
        try:
            text = load_skill(name)
            print(f"{name:24} OK ({len(text)} chars)")
        except Exception as exc:
            print(f"{name:24} FAIL ({exc})")
            hard_failures.append(f"Missing/broken skill: {name}")

    print("\n[Planning LLM]")
    vilao_key = bool(os.getenv("VILAO_API_KEY", "").strip())
    vilao_model = os.getenv("VILAO_MODEL", "").strip()
    print(f"VILAO_API_KEY          {yes_no(vilao_key)}")
    print(f"VILAO_MODEL            {vilao_model or 'MISSING'}")
    if not vilao_key:
        hard_failures.append("VILAO_API_KEY is missing.")
    if not vilao_model:
        hard_failures.append("VILAO_MODEL is missing.")

    print("\n[Gemini multimodal review]")
    gemini_key = bool(
        (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    )
    visual_model = os.getenv(
        "VISUAL_REVIEW_MODEL",
        "gemini-2.5-flash",
    ).strip()
    google_genai = importlib.util.find_spec("google.genai") is not None
    print(f"Gemini API key         {yes_no(gemini_key)}")
    print(f"google-genai           {yes_no(google_genai)}")
    print(f"VISUAL_REVIEW_MODEL    {visual_model or 'MISSING'}")
    if not gemini_key:
        optional.append(
            "Gemini key missing: automated Visual Review will be unavailable."
        )
    if not google_genai:
        optional.append(
            "google-genai missing: run pip install -r requirements-orchestrator.txt."
        )

    print("\n[Local media tools]")
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    print(f"ffmpeg                 {ffmpeg or 'MISSING'}")
    print(f"ffprobe                {ffprobe or 'MISSING'}")
    if not ffmpeg:
        optional.append("FFmpeg missing: final media assembly cannot run yet.")
    if not ffprobe:
        optional.append("ffprobe missing: media diagnostics will be limited.")

    print("\n[Audio upstream repos]")
    audio_paths = {
        "Chatterbox": ROOT / "vendor" / "chatterbox",
        "MMAudio": ROOT / "vendor" / "mmaudio",
        "ACE-Step": ROOT / "vendor" / "ace-step",
    }
    for name, path in audio_paths.items():
        exists = path.exists()
        print(f"{name:24} {yes_no(exists)}  {path}")
        if not exists:
            optional.append(
                f"{name} vendor repo not found; audio stage not ready yet."
            )

    print("\n[Project]")
    required = [
        ROOT / "config" / "series_bible.json",
        ROOT / "config" / "character_bible.json",
        ROOT / "config" / "environment_bible.json",
        ROOT / "config" / "reference_asset_prompts.json",
    ]
    for path in required:
        exists = path.exists()
        print(f"{path.name:24} {yes_no(exists)}")
        if not exists:
            hard_failures.append(f"Missing project config: {path.name}")

    print("\n=== RESULT ===")
    if hard_failures:
        print("BLOCKED")
        for item in hard_failures:
            print(f"- {item}")
    else:
        print("PLANNING PIPELINE READY")

    if optional:
        print("\nLater-stage items:")
        for item in optional:
            print(f"- {item}")

    return 1 if hard_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
