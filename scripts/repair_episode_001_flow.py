from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.state_manager import EpisodeStateManager


SOFT_SOFT_TARGET_SECONDS = 60.0
MAX_WORDS_PER_SECOND = 2.55
MIN_SCENE_SECONDS = 4.0

PREFERRED_DURATIONS = {
    "scene_1_hook": 6.0,
    "scene_2_problem": 12.0,
    "scene_3_observation": 9.0,
    "scene_4_explanation": 13.0,
    "scene_5_realization": 8.0,
    "scene_6_interview_question": 5.0,
    "scene_7_concise_answer": 10.0,
    "scene_8_resolution": 4.0,
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def backup_once(path: Path) -> None:
    backup = path.with_suffix(path.suffix + ".pre_flow_repair")
    if not backup.exists():
        shutil.copy2(path, backup)


def word_count(scene: dict) -> int:
    return sum(
        len(str(line.get("text") or "").split())
        for line in scene.get("dialogue", [])
    )


def min_duration(scene: dict) -> float:
    words = word_count(scene)
    if not words:
        return float(MIN_SCENE_SECONDS)

    raw = words / MAX_WORDS_PER_SECOND
    speech = math.ceil(raw * 2.0) / 2.0
    return float(max(MIN_SCENE_SECONDS, speech))


def preferred_durations(script_scenes: list[dict]) -> list[float] | None:
    ids = [scene.get("scene_id") for scene in script_scenes]
    if set(ids) != set(PREFERRED_DURATIONS):
        return None

    values = [PREFERRED_DURATIONS[sid] for sid in ids]
    minimums = [min_duration(scene) for scene in script_scenes]

    # Quality-first: a preferred duration is a floor, not a hard episode cap.
    # If approved dialogue needs more room, expand that scene instead of
    # stealing time from another scene.
    adjusted = [
        max(preferred, minimum)
        for preferred, minimum in zip(values, minimums)
    ]
    return [round(value * 2.0) / 2.0 for value in adjusted]

def allocate_durations(script_scenes: list[dict]) -> list[float]:
    preferred = preferred_durations(script_scenes)
    if preferred is not None:
        return preferred

    durations: list[float] = []
    for scene in script_scenes:
        original = float(scene["end_s"]) - float(scene["start_s"])
        minimum = min_duration(scene)
        # Keep original creative pacing when it is already generous.
        # Otherwise expand only the scene that needs more room.
        durations.append(
            round(max(original, minimum) * 2.0) / 2.0
        )
    return durations

def replace_ci(text: str | None, old: str, new: str) -> str | None:
    if text is None:
        return None
    return re.sub(re.escape(old), new, text, flags=re.IGNORECASE)


def clean_audio_conflicts(text: str) -> str:
    phrases = [
        "No spoken dialogue audio.",
        "No dialogue audio.",
        "No spoken audio.",
    ]
    for phrase in phrases:
        text = text.replace(phrase, "")
    return re.sub(r"\s{2,}", " ", text).strip()


def normalize_prompt_duration(text: str, duration: float) -> str:
    seconds = (
        str(int(duration))
        if float(duration).is_integer()
        else f"{duration:.1f}"
    )
    patterns = [