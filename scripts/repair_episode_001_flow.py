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


TARGET_SECONDS = 60.0
MAX_WORDS_PER_SECOND = 2.55
MIN_SCENE_SECONDS = 4.0

PREFERRED_DURATIONS = {
    "scene_1_hook": 5.5,
    "scene_2_problem": 11.0,
    "scene_3_observation": 7.5,
    "scene_4_explanation": 11.0,
    "scene_5_realization": 8.0,
    "scene_6_interview_question": 4.0,
    "scene_7_concise_answer": 9.0,
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
    if abs(sum(values) - TARGET_SECONDS) > 0.01:
        raise RuntimeError(
            f"Preferred durations must total {TARGET_SECONDS:.1f}s, "
            f"got {sum(values):.1f}s."
        )

    minimums = [min_duration(scene) for scene in script_scenes]

    # Raise any preferred slot that is below its dialogue-safe minimum,
    # then borrow the same amount from scenes that still have slack.
    adjusted = list(values)
    deficit = 0.0
    for index, minimum in enumerate(minimums):
        if adjusted[index] < minimum:
            deficit += minimum - adjusted[index]
            adjusted[index] = minimum

    if deficit > 0:
        donor_order = sorted(
            range(len(adjusted)),
            key=lambda i: adjusted[i] - minimums[i],
            reverse=True,
        )
        for index in donor_order:
            slack = adjusted[index] - minimums[index]
            if slack <= 0:
                continue
            take = min(slack, deficit)
            # keep half-second precision
            take = math.floor(take * 2.0) / 2.0
            if take <= 0:
                continue
            adjusted[index] -= take
            deficit -= take
            if deficit <= 0.001:
                break

    if deficit > 0.001:
        raise RuntimeError(
            "Preferred 60s schedule cannot satisfy dialogue-safe minimums. "
            f"Unresolved deficit: {deficit:.1f}s."
        )

    drift = TARGET_SECONDS - sum(adjusted)
    if abs(drift) > 0.001:
        donor_order = sorted(
            range(len(adjusted)),
            key=lambda i: adjusted[i] - minimums[i],
            reverse=True,
        )
        if drift > 0:
            adjusted[donor_order[0]] += drift
        else:
            remaining = -drift
            for index in donor_order:
                slack = adjusted[index] - minimums[index]
                take = min(slack, remaining)
                adjusted[index] -= take
                remaining -= take
                if remaining <= 0.001:
                    break
            if remaining > 0.001:
                raise RuntimeError(
                    "Could not normalize preferred schedule to exactly 60s."
                )

    return [round(value * 2.0) / 2.0 for value in adjusted]


def allocate_durations(script_scenes: list[dict]) -> list[float]:
    preferred = preferred_durations(script_scenes)
    if preferred is not None:
        return preferred
    original = [
        float(scene["end_s"]) - float(scene["start_s"])
        for scene in script_scenes
    ]
    minimums = [min_duration(scene) for scene in script_scenes]
    minimum_total = sum(minimums)

    if minimum_total > TARGET_SECONDS:
        raise RuntimeError(
            f"Exact approved dialogue needs at least {minimum_total:.1f}s "
            f"at {MAX_WORDS_PER_SECOND:.2f} words/s, exceeding the "
            f"{TARGET_SECONDS:.1f}s episode target."
        )

    target = TARGET_SECONDS
    extra = target - minimum_total

    weights = [
        max(0.5, original[i] - minimums[i] + 1.0)
        for i in range(len(original))
    ]
    weight_total = sum(weights)

    durations = [
        minimums[i] + (extra * weights[i] / weight_total if weight_total else 0)
        for i in range(len(original))
    ]

    # Use half-second precision while preserving exact total.
    rounded = [round(value * 2) / 2 for value in durations]
    drift = round(target - sum(rounded), 1)
    rounded[-1] = round((rounded[-1] + drift) * 2) / 2

    if rounded[-1] < MIN_SCENE_SECONDS:
        deficit = MIN_SCENE_SECONDS - rounded[-1]
        rounded[-1] = MIN_SCENE_SECONDS
        for i in range(len(rounded) - 1):
            spare = rounded[i] - minimums[i]
            take = min(spare, deficit)
            rounded[i] -= take
            deficit -= take
            if deficit <= 0:
                break
        if deficit > 0:
            raise RuntimeError("Could not allocate safe scene durations.")

    return rounded


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