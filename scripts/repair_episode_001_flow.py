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
    "scene_3_observation": 8.0,
    "scene_4_explanation": 11.0,
    "scene_5_realization": 7.5,
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
        r"Duration\s+\d+(?:\.\d+)?\s+seconds",
        r"Target duration:\s*\d+(?:\.\d+)?\s+seconds",
    ]
    for pattern in patterns:
        replacement = (
            f"Duration {seconds} seconds"
            if pattern.startswith("Duration")
            else f"Target duration: {seconds} seconds"
        )
        text = re.sub(
            pattern,
            replacement,
            text,
            flags=re.IGNORECASE,
        )
    return text


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
        veo_by_id[sid]["prompt"] = normalize_prompt_duration(
            veo_by_id[sid]["prompt"],
            duration,
        )
        cursor += duration

    script["duration_s"] = cursor

    # scene_1_hook: one primary action in a short vertical clip.
    sid = "scene_1_hook"
    if sid in scenes_by_id(script):
        scene = scenes_by_id(script)[sid]
        scene["visual_action"] = (
            "Tiny Cadet is already positioned screen-right beside the fuel line and points "
            "toward the pipe running screen-left to screen-right; Chief Engineer remains "
            "screen-left and makes only a small head turn toward him."
        )
    if sid in veo_by_id:
        prompt = veo_by_id[sid]["prompt"]
        prompt = re.sub(
            r"Tiny Cadet enters frame from the right.*?Chief Engineer in dark navy coverall and white helmet stands left in relaxed posture, turns his head toward Tiny Cadet\.",
            "Tiny Cadet is already positioned screen-right beside the fuel line and points toward the pipe running screen-left to screen-right; Chief Engineer remains screen-left and makes only a small head turn toward Tiny Cadet.",
            prompt,
            flags=re.IGNORECASE,
        )
        veo_by_id[sid]["prompt"] = clean_audio_conflicts(prompt)

    if sid in board_by_id:
        board_by_id[sid]["camera"] = (
            "Fixed three-quarter-left angle, eye-level, locked-off; no camera movement."
        )

    # scene_2_problem: dialogue-first, one simple composition, no overlay/cutaway.
    sid = "scene_2_problem"
    if sid in scenes_by_id(script):
        scene = scenes_by_id(script)[sid]
        scene["visual_action"] = (
            "Tiny Cadet remains screen-right beside the fuel pipe and looks concerned; "
            "Chief Engineer remains screen-left and gives one small confirming nod. "
            "The fuel pipe continues screen-left to screen-right."
        )
    if sid in board_by_id:
        board = board_by_id[sid]
        board["camera"] = (
            "Fixed eye-level medium two-shot; no dolly, pan, truck, or cutaway."
        )
        board["composition"] = (
            "Tiny Cadet screen-right, Chief Engineer screen-left, fuel pipe crossing "
            "the lower frame screen-left to screen-right in vertical 9:16."
        )
        board["technical_visualization"] = None
    if sid in veo_by_id:
        prompt = veo_by_id[sid]["prompt"]
        # Remove any imagined/cutaway/overlay sentences.
        prompt = re.sub(
            r"\s*In the upper-center safe area.*?(?:no text labels\.|camera shake)",
            "",
            prompt,
            flags=re.IGNORECASE,
        )
        prompt = re.sub(
            r"Visible action:.*?Blocking:",
            "Visible action: Tiny Cadet remains screen-right beside the fuel pipe and looks concerned; Chief Engineer remains screen-left and gives one small confirming nod. The fuel pipe continues screen-left to screen-right. Blocking:",
            prompt,
            flags=re.IGNORECASE,
        )
        prompt = re.sub(
            r"Blocking:.*?Lighting:",
            "Blocking: fixed eye-level medium two-shot, no camera movement; Tiny Cadet screen-right, Chief Engineer screen-left, pipe crossing lower frame left-to-right in the vertical 9:16 safe area. Lighting:",
            prompt,
            flags=re.IGNORECASE,
        )
        veo_by_id[sid]["prompt"] = clean_audio_conflicts(prompt)
        veo_by_id[sid]["negative_prompt"] = clean_negative(
            veo_by_id[sid]["negative_prompt"]
        )

    # scene_2 is intentionally static after QA repair; do not reintroduce camera motion.

    # scene_3_observation: one camera move, realistic rotation wording.
    sid = "scene_3_observation"
    if sid in board_by_id:
        board_by_id[sid]["camera"] = (
            "Fixed eye-level medium shot centered on the purifier; no truck or pan."
        )
    if sid in veo_by_id:
        prompt = veo_by_id[sid]["prompt"]
        prompt = replace_ci(
            prompt,
            "camera trucks right with Tiny Cadet then settles locked on the purifier",
            "camera remains fixed in an eye-level medium shot centered on the purifier",
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

    # scene_3: remove walk+truck overload; character is already at purifier.
    sid = "scene_3_observation"
    if sid in scenes_by_id(script):
        scene = scenes_by_id(script)[sid]
        scene["visual_action"] = (
            "Tiny Cadet is already beside the purifier and looks at it; "
            "Chief Engineer remains screen-left and makes one open-palm gesture toward the machine."
        )
    if sid in board_by_id:
        board = board_by_id[sid]
        board["camera"] = (
            "Fixed eye-level medium shot centered on the purifier; no truck or pan."
        )
        board["composition"] = (
            "Purifier centered, inlet screen-left, outlet screen-right; "
            "Chief Engineer screen-left and Tiny Cadet screen-right in vertical 9:16."
        )
    if sid in veo_by_id:
        prompt = veo_by_id[sid]["prompt"]
        prompt = re.sub(
            r"Visible action:.*?Blocking:",
            "Visible action: Tiny Cadet is already beside the purifier on screen-right and looks at it; Chief Engineer remains screen-left and makes one small open-palm gesture toward the machine. Blocking:",
            prompt,
            flags=re.IGNORECASE,
        )
        prompt = re.sub(
            r"Blocking:.*?The purifier bowl",
            "Blocking: fixed eye-level medium shot centered on the purifier; inlet screen-left, outlet screen-right, Chief Engineer screen-left and Tiny Cadet screen-right in the vertical 9:16 safe area. The purifier bowl",
            prompt,
            flags=re.IGNORECASE,
        )
        veo_by_id[sid]["prompt"] = clean_audio_conflicts(prompt)

    # scene_4_explanation: preserve only supported centrifugal-separation concept.
    sid = "scene_4_explanation"
    if sid in board_by_id:
        board = board_by_id[sid]
        board["camera"] = (
            "Fixed eye-level medium shot centered on the purifier cutaway; "
            "Chief and Cadet remain small edge-of-frame supporting figures; no camera movement."
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
            "50mm fixed eye-level medium shot centered on the purifier bowl and cutaway",
        )
        prompt = replace_ci(
            prompt,
            "one rack focus from Chief Engineer's face to the purifier cutaway",
            "stable focus on the purifier cutaway; characters remain secondary",
        )
        prompt = replace_ci(
            prompt,
            "denser water and solid particles pulled outward to the bowl wall",
            "water and solid impurities move outward by centrifugal separation",
        )
        prompt = re.sub(
            r"fuel entering the center,\s*water and solid impurities move outward by centrifugal separation,\s*and cleaner fuel exiting from the center toward the outlet",
            "dirty fuel entering, water and solid impurities moving outward by centrifugal separation, and cleaner fuel leaving",
            prompt,
            flags=re.IGNORECASE,
        )
        prompt = re.sub(
            r"fuel entering the center,\s*denser water and solid particles pulled outward to the bowl wall,\s*and cleaner fuel exiting from the center toward the outlet",
            "dirty fuel entering, water and solid impurities moving outward by centrifugal separation, and cleaner fuel leaving",
            prompt,
            flags=re.IGNORECASE,
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

    # scene_6: explicitly motivate the return to the purifier area.
    sid = "scene_6_interview_question"
    if sid in scenes_by_id(script):
        scene = scenes_by_id(script)[sid]
        scene["visual_action"] = (
            "The shot briefly re-establishes the purifier area. Chief Engineer "
            "turns toward Tiny Cadet and asks the interview question; Tiny Cadet "
            "straightens and listens."
        )
    if sid in veo_by_id:
        prompt = veo_by_id[sid]["prompt"]
        prompt = replace_ci(
            prompt,
            "returns to the purifier area",
            "briefly re-establishes the purifier area after the previous engineward movement",
        )
        veo_by_id[sid]["prompt"] = clean_audio_conflicts(prompt)

    # scene_7: protect the long exact answer with a static speaking shot.
    sid = "scene_7_concise_answer"
    if sid in scenes_by_id(script):
        scene = scenes_by_id(script)[sid]
        scene["visual_action"] = (
            "Tiny Cadet faces Chief Engineer and delivers the approved answer steadily. "
            "Chief Engineer listens and gives one small approving nod at the end."
        )
    if sid in board_by_id:
        board_by_id[sid]["camera"] = (
            "Fixed eye-level medium close-up on Tiny Cadet; no dolly, pan, or glance choreography."
        )
    if sid in veo_by_id:
        prompt = veo_by_id[sid]["prompt"]
        prompt = re.sub(
            r"Visible action:.*?Blocking:",
            "Visible action: Tiny Cadet faces Chief Engineer and delivers the approved answer steadily; Chief Engineer listens and gives one small approving nod only at the end. Blocking:",
            prompt,
            flags=re.IGNORECASE,
        )
        prompt = re.sub(
            r"Blocking:.*?Lighting:",
            "Blocking: fixed eye-level medium close-up on Tiny Cadet; Chief Engineer remains at the left edge and purifier stays softly visible in the right background; no dolly, pan, or glance choreography. Lighting:",
            prompt,
            flags=re.IGNORECASE,
        )
        veo_by_id[sid]["prompt"] = clean_audio_conflicts(prompt)

    # scene_7: one dominant camera idea only.
    sid = "scene_7_concise_answer"
    if sid in board_by_id:
        board_by_id[sid]["camera"] = (
            "Fixed eye-level medium close-up on Tiny Cadet; no camera movement."
        )
    if sid in veo_by_id:
        prompt = replace_ci(
            veo_by_id[sid]["prompt"],
            "locked off then a very slow dolly in",
            "fixed eye-level medium close-up",
        )
        veo_by_id[sid]["prompt"] = clean_audio_conflicts(prompt)

    # Strengthen generic text/signage blocking for every Flow scene.
    for item in veo.get("scenes", []):
        existing = [
            part.strip()
            for part in item.get("negative_prompt", "").split(",")
            if part.strip()
        ]
        required = [
            "readable machinery text",
            "random signage",
            "on-screen text",
        ]
        lower = {part.lower() for part in existing}
        for term in required:
            if term.lower() not in lower:
                existing.append(term)
        item["negative_prompt"] = ", ".join(existing)

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
    if abs(float(script["duration_s"]) - TARGET_SECONDS) > 0.01:
        raise RuntimeError(
            f"Episode duration is not exactly {TARGET_SECONDS:.1f}s: "
            f"{script['duration_s']}"
        )
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

        vp = next(item for item in veo["scenes"] if item["scene_id"] == sid)
        if abs(float(vp["duration_s"]) - duration) > 0.01:
            raise RuntimeError(
                f"Veo duration mismatch for {sid}: "
                f"{vp['duration_s']} vs {duration}"
            )
        text = vp["prompt"]
        match = re.search(
            r"Duration\s+(\d+(?:\.\d+)?)\s+seconds",
            text,
            flags=re.IGNORECASE,
        )
        if match and abs(float(match.group(1)) - duration) > 0.01:
            raise RuntimeError(
                f"Embedded prompt duration mismatch for {sid}: "
                f"{match.group(1)} vs {duration}"
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