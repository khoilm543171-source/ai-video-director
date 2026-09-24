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
MAX_WORDS_PER_SECOND = 2.5
MIN_SCENE_SECONDS = 4.0


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
    speakers = {
        line.get("character")
        for line in scene.get("dialogue", [])
        if line.get("character")
    }
    speech = math.ceil(words / MAX_WORDS_PER_SECOND) if words else 0
    if words and len(speakers) > 1:
        speech += 1
    return float(max(MIN_SCENE_SECONDS, speech))


def allocate_durations(script_scenes: list[dict]) -> list[float]:
    original = [
        float(scene["end_s"]) - float(scene["start_s"])
        for scene in script_scenes
    ]
    minimums = [min_duration(scene) for scene in script_scenes]
    minimum_total = sum(minimums)

    target = max(TARGET_SECONDS, minimum_total)
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


def clean_negative(text: str) -> str:
    blocked = {
        "dialogue audio",
        "speech",
        "vocals",
        "lip-sync mouth shapes for spoken words",
    }
    parts = [part.strip() for part in text.split(",") if part.strip()]
    return ", ".join(part for part in parts if part.lower() not in blocked)


def patch_episode(
    script: dict,
    storyboard: dict,
    veo: dict,
) -> None:
    scenes = script["scenes"]
    durations = allocate_durations(scenes)

    board_by_id = {item["scene_id"]: item for item in storyboard["scenes"]}
    veo_by_id = {item["scene_id"]: item for item in veo["scenes"]}

    cursor = 0.0
    for scene, duration in zip(scenes, durations):
        sid = scene["scene_id"]
        scene["start_s"] = cursor
        scene["end_s"] = cursor + duration
        board_by_id[sid]["start_s"] = cursor
        board_by_id[sid]["end_s"] = cursor + duration
        veo_by_id[sid]["duration_s"] = duration
        cursor += duration

    script["duration_s"] = cursor

    # scene_2_problem: keep performance + one slow dolly; move separation cutaway to scene 4.
    sid = "scene_2_problem"
    if sid in board_by_id:
        board = board_by_id[sid]
        board["camera"] = (
            "Single slow eye-level dolly-in toward Tiny Cadet; no second camera move."
        )
        board["technical_visualization"] = None
    if sid in veo_by_id:
        prompt = veo_by_id[sid]["prompt"]
        prompt = re.sub(
            r"\s*In the upper-center safe area.*?no text labels\.",
            "",
            prompt,
            flags=re.IGNORECASE,
        )
        prompt = replace_ci(
            prompt,
            "35mm natural lens, eye-level, slow dolly in toward Tiny Cadet",
            "35mm natural lens, eye-level, one slow dolly-in toward Tiny Cadet",
        )
        veo_by_id[sid]["prompt"] = clean_audio_conflicts(prompt)
        veo_by_id[sid]["negative_prompt"] = clean_negative(
            veo_by_id[sid]["negative_prompt"]
        )

    # scene_3_observation: one camera move, realistic rotation wording.
    sid = "scene_3_observation"
    if sid in board_by_id:
        board_by_id[sid]["camera"] = (
            "Single slow eye-level truck-right following Tiny Cadet and ending "
            "with the purifier centered; no lock-off transition."
        )
    if sid in veo_by_id:
        prompt = veo_by_id[sid]["prompt"]
        prompt = replace_ci(
            prompt,
            "camera trucks right with Tiny Cadet then settles locked on the purifier",
            "camera makes one slow truck-right following Tiny Cadet and ends with the purifier centered",
        )
        prompt = replace_ci(
            prompt,
            "subtle vibration-free motion blur",
            "soft realistic motion blur",
        )
        veo_by_id[sid]["prompt"] = clean_audio_conflicts(prompt)
        veo_by_id[sid]["negative_prompt"] = clean_negative(
            veo_by_id[sid]["negative_prompt"]
        )

    # scene_4_explanation: preserve only supported centrifugal-separation concept.
    sid = "scene_4_explanation"
    if sid in board_by_id:
        board = board_by_id[sid]
        board["camera"] = (
            "Locked-off slight high three-quarter view; stable focus, no rack focus."
        )
        if board.get("technical_visualization"):
            board["technical_visualization"] = replace_ci(
                board["technical_visualization"],
                "denser water and solid particles",
                "water and solid impurities",
            )
    if sid in veo_by_id:
        prompt = veo_by_id[sid]["prompt"]
        prompt = replace_ci(
            prompt,
            "50mm portrait feel, eye-level, locked off with a slight high angle on the purifier bowl",
            "50mm portrait feel, locked-off slight high three-quarter view of the purifier bowl",
        )
        prompt = replace_ci(
            prompt,
            "one rack focus from Chief Engineer's face to the purifier cutaway",
            "stable focus that keeps the Chief Engineer and purifier cutaway readable",
        )
        prompt = replace_ci(
            prompt,
            "denser water and solid particles pulled outward to the bowl wall",
            "water and solid impurities move outward by centrifugal separation",
        )
        veo_by_id[sid]["prompt"] = clean_audio_conflicts(prompt)
        veo_by_id[sid]["negative_prompt"] = clean_negative(
            veo_by_id[sid]["negative_prompt"]
        )

    # scene_5_realization: remove unsupported "last cleaning step" claim.
    sid = "scene_5_realization"
    if sid in scenes_by_id(script):
        scene = scenes_by_id(script)[sid]
        scene["visual_action"] = replace_ci(
            scene.get("visual_action"),
            "the purifier is the last cleaning step",
            "cleaner fuel continues from the purifier toward the engine",
        )
        scene["technical_point"] = replace_ci(
            scene.get("technical_point"),
            "last cleaning step",
            "cleaner fuel supply toward the engine",
        )
    if sid in veo_by_id:
        prompt = replace_ci(
            veo_by_id[sid]["prompt"],
            "the purifier is the last cleaning step",
            "cleaner fuel continues from the purifier toward the engine",
        )
        veo_by_id[sid]["prompt"] = clean_audio_conflicts(prompt)
        veo_by_id[sid]["negative_prompt"] = clean_negative(
            veo_by_id[sid]["negative_prompt"]
        )

    # Remove legacy audio suppression from every speaking scene.
    for scene in scenes:
        if not scene.get("dialogue"):
            continue
        sid = scene["scene_id"]
        if sid not in veo_by_id:
            continue
        veo_by_id[sid]["prompt"] = clean_audio_conflicts(
            veo_by_id[sid]["prompt"]
        )
        veo_by_id[sid]["negative_prompt"] = clean_negative(
            veo_by_id[sid]["negative_prompt"]
        )


def scenes_by_id(script: dict) -> dict[str, dict]:
    return {
        scene["scene_id"]: scene
        for scene in script.get("scenes", [])
    }


def verify(script: dict, storyboard: dict, veo: dict) -> None:
    script_ids = [scene["scene_id"] for scene in script["scenes"]]
    board_ids = [scene["scene_id"] for scene in storyboard["scenes"]]
    veo_ids = [scene["scene_id"] for scene in veo["scenes"]]
    if not (script_ids == board_ids == veo_ids):
        raise RuntimeError("Scene ids diverged during repair.")

    for scene in script["scenes"]:
        sid = scene["scene_id"]
        duration = float(scene["end_s"]) - float(scene["start_s"])
        words = word_count(scene)
        rate = words / duration if duration else 999
        if words and rate > MAX_WORDS_PER_SECOND + 0.01:
            raise RuntimeError(
                f"{sid} still has {words} words in {duration:.1f}s "
                f"({rate:.2f} w/s)."
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply deterministic Flow-QA repairs to Episode 001."
    )
    parser.add_argument(
        "--episode-id",
        default="episode_001_fuel_oil_purifier",
    )
    args = parser.parse_args()

    root = PROJECT_ROOT / "outputs" / "episodes"
    state = EpisodeStateManager(root)
    manifest = state.load_manifest(args.episode_id)
    episode_dir = Path(manifest.output_dir)

    paths = {
        "script": episode_dir / "script.json",
        "storyboard": episode_dir / "storyboard.json",
        "veo": episode_dir / "veo_prompts.json",
    }
    for path in paths.values():
        if not path.exists():
            raise FileNotFoundError(path)
        backup_once(path)

    script = load_json(paths["script"])
    storyboard = load_json(paths["storyboard"])
    veo = load_json(paths["veo"])

    patch_episode(script, storyboard, veo)
    verify(script, storyboard, veo)

    write_json(paths["script"], script)
    write_json(paths["storyboard"], storyboard)
    write_json(paths["veo"], veo)

    review_path = episode_dir / "flow_prompt_review.json"
    if review_path.exists():
        review_path.unlink()

    print(f"Repaired episode: {args.episode_id}")
    print(f"New duration    : {script['duration_s']:.1f}s")
    print("Scene timing:")
    for scene in script["scenes"]:
        duration = scene["end_s"] - scene["start_s"]
        words = word_count(scene)
        rate = words / duration if duration else 0
        print(
            f"  {scene['scene_id']}: {duration:.1f}s, "
            f"{words} words, {rate:.2f} w/s"
        )
    print()
    print("Backups were saved as *.pre_flow_repair.")
    print("Next: rerun scripts/review_flow_prompts.py")


if __name__ == "__main__":
    raise SystemExit(main())
