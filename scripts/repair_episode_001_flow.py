from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.state_manager import EpisodeStateManager


SOFT_TARGET_SECONDS = 60.0
MAX_WORDS_PER_SECOND = 2.55

# Quality-first timings for Episode 001.
# 60 seconds is only a soft target; these clips may exceed it when needed.
PREFERRED_DURATIONS = {
    "scene_1_hook": 6.0,
    "scene_2_problem": 12.0,
    "scene_3_observation": 9.0,
    "scene_4_explanation": 13.0,
    "scene_5_realization": 8.0,
    "scene_6_interview_question": 5.0,
    "scene_7_concise_answer": 12.0,
    "scene_8_resolution": 4.0,
}


SCENE_VISUALS = {
    "scene_1_hook": {
        "action": (
            "Tiny Cadet is already positioned screen-right beside the fuel oil pipe "
            "and points toward it. Chief Engineer remains screen-left and makes only "
            "a small head turn toward Tiny Cadet."
        ),
        "camera": (
            "Fixed three-quarter-left angle, eye-level, medium-wide shot, locked-off. "
            "No camera movement."
        ),
        "composition": (
            "Fuel pipe runs screen-left to screen-right through the lower frame. "
            "Chief Engineer stays screen-left, Tiny Cadet screen-right, both readable "
            "inside the vertical 9:16 safe area."
        ),
        "technical": None,
    },
    "scene_2_problem": {
        "action": (
            "Tiny Cadet remains screen-right beside the fuel pipe and looks concerned. "
            "Chief Engineer remains screen-left and gives one small confirming nod."
        ),
        "camera": (
            "Fixed eye-level medium two-shot. No dolly, pan, truck, overlay, cutaway, "
            "or secondary camera move."
        ),
        "composition": (
            "Tiny Cadet screen-right, Chief Engineer screen-left, fuel pipe crossing "
            "the lower frame screen-left to screen-right."
        ),
        "technical": None,
        "dialogue_pacing": (
            "Tiny Cadet speaks first from about 0.5s to 3.0s. Pause briefly. "
            "Chief Engineer replies from about 3.5s to 11.5s. "
            "Keep the nod after the Chief Engineer finishes speaking."
        ),
    },
    "scene_3_observation": {
        "action": (
            "Tiny Cadet is already beside the purifier on screen-right and looks at it. "
            "Chief Engineer remains screen-left and makes one small open-palm gesture "
            "toward the purifier. The purifier bowl rotates with soft realistic motion blur."
        ),
        "camera": (
            "Fixed eye-level medium shot centered on the purifier. No truck, pan, or dolly."
        ),
        "composition": (
            "Purifier centered and fully inside the vertical 9:16 safe area, inlet "
            "screen-left, outlet screen-right. Chief Engineer remains lower-left and "
            "Tiny Cadet lower-right as supporting figures."
        ),
        "technical": None,
        "dialogue_pacing": (
            "Chief Engineer speaks first, then pause briefly, then Tiny Cadet speaks. "
            "Keep both approved lines sequential with no overlap."
        ),
    },
    "scene_4_explanation": {
        "action": (
            "The purifier cutaway is the primary visual. Use only two readable beats: "
            "dirty fuel entering, then cleaner fuel leaving. During both beats, suggest "
            "centrifugal separation only as one continuous background effect showing "
            "water and solid impurities being removed. Chief Engineer and Tiny Cadet "
            "remain small supporting figures at the frame edges."
        ),
        "camera": (
            "Fixed eye-level medium-wide shot centered on the purifier cutaway. "
            "Stable focus, no rack focus and no camera movement."
        ),
        "composition": (
            "Purifier and cutaway dominate the center of the vertical frame. Chief Engineer "
            "is small at the left edge and Tiny Cadet small at the right edge."
        ),
        "technical": (
            "Show only the approved concept that centrifugal separation removes water "
            "and solid impurities from fuel oil. The cutaway may suggest spinning and "
            "separation, but must not claim exact internal flow paths or mechanical internals. "
            "Do not add RPM, temperatures, maintenance, alarms, intervals, regulations, "
            "or troubleshooting."
        ),
    },
    "scene_5_realization": {
        "action": (
            "Cleaner fuel continues from the purifier toward the engine. Tiny Cadet follows "
            "the pipe direction with his eyes and makes one small realization gesture. "
            "Chief Engineer remains a quiet supporting presence."
        ),
        "camera": (
            "Gentle tracking pan right that keeps Tiny Cadet centered while following the "
            "fuel line screen-left to screen-right toward the engine."
        ),
        "composition": (
            "Tiny Cadet remains inside the vertical center safe area. Fuel flow direction "
            "stays screen-left to screen-right."
        ),
        "technical": (
            "Cleaner fuel is supplied toward the engine after water and solid impurities "
            "are removed. Do not call the purifier the last cleaning step."
        ),
    },
    "scene_6_interview_question": {
        "action": (
            "Briefly re-establish the purifier area after the previous engineward movement. "
            "Chief Engineer turns toward Tiny Cadet and asks the interview question. "
            "Tiny Cadet straightens and listens."
        ),
        "camera": (
            "Fixed eye-level medium two-shot. No camera movement."
        ),
        "composition": (
            "Chief Engineer screen-left, Tiny Cadet screen-right, purifier softly visible "
            "between or behind them to motivate the return to the interview position."
        ),
        "technical": None,
    },
    "scene_7_concise_answer": {
        "action": (
            "Tiny Cadet faces Chief Engineer and delivers the approved answer steadily. "
            "Chief Engineer listens and gives one small approving nod only after the answer."
        ),
        "camera": (
            "Fixed eye-level medium close-up on Tiny Cadet. No dolly, pan, tilt, reframe, "
            "or additional choreography during the answer. Keep the purifier softly visible "
            "as a static background element."
        ),
        "composition": (
            "Maintain Chief Engineer screen-left and Tiny Cadet screen-right as in scene_6; "
            "do not reverse screen direction. Tiny Cadet is the clear center subject and the "
            "purifier stays softly visible as a static background element."
        ),
        "technical": (
            "Keep the exact approved answer from script.json. Do not expand beyond removing "
            "water and solid impurities by centrifugal separation so cleaner fuel is supplied "
            "to the engine."
        ),
        "dialogue_pacing": (
            "Tiny Cadet delivers the full approved answer from about 0.5s to 10.5s "
            "at a clear, measured but brisk pace. Chief Engineer gives one small approving "
            "nod only after the final word, around 10.8s to 11.6s."
        ),
    },
    "scene_8_resolution": {
        "action": (
            "Chief Engineer gives one calm approving nod. Tiny Cadet relaxes slightly. "
            "No new technical action is introduced."
        ),
        "camera": (
            "Fixed eye-level medium two-shot. No camera movement."
        ),
        "composition": (
            "Chief Engineer screen-left, Tiny Cadet screen-right, purifier softly visible "
            "in the background for closure."
        ),
        "technical": None,
    },
}


GLOBAL_NEGATIVES = [
    "character drift",
    "changed face",
    "changed clothing",
    "changed helmet color",
    "wrong PPE",
    "duplicate people",
    "extra limbs",
    "malformed hands",
    "unreadable machinery geometry",
    "fantasy machinery",
    "random logos",
    "readable machinery text",
    "readable gauge text",
    "random signage",
    "on-screen text",
    "subtitles",
    "baked-in captions",
    "camera shake",
    "background music",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def backup_once(path: Path) -> None:
    backup = path.with_suffix(path.suffix + ".quality_first_backup")
    if not backup.exists():
        shutil.copy2(path, backup)


def word_count(scene: dict) -> int:
    return sum(
        len(str(line.get("text") or "").split())
        for line in scene.get("dialogue", [])
    )


def clean_negative(existing: str) -> str:
    blocked = {
        "dialogue audio",
        "speech",
        "vocals",
        "lip-sync mouth shapes for spoken words",
        "no spoken dialogue audio",
        "no dialogue audio",
    }
    values = [
        item.strip()
        for item in str(existing or "").split(",")
        if item.strip()
    ]

    kept: list[str] = []
    seen: set[str] = set()
    for item in [*values, *GLOBAL_NEGATIVES]:
        lowered = item.lower()
        if lowered in blocked or lowered in seen:
            continue
        kept.append(item)
        seen.add(lowered)

    return ", ".join(kept)


def build_visual_prompt(
    scene_id: str,
    duration: float,
    visual: dict,
) -> str:
    lines = [
        "Tiny cute stylized 3D animation with miniature proportions, cinematic "
        "educational tone, physically believable merchant ship engine room.",
        "",
        f"Duration {duration:.1f} seconds. Native vertical 9:16.",
        "",
        "VISIBLE ACTION:",
        visual["action"],
        "",
        "CAMERA:",
        visual["camera"],
        "",
        "COMPOSITION / CONTINUITY:",
        visual["composition"],
        "",
        "LIGHTING:",
        "Warm practical engine-room lighting with soft cinematic rim light. "
        "Preserve the same industrial palette, machinery scale and environment.",
    ]
    if visual.get("technical"):
        lines.extend(
            [
                "",
                "TECHNICAL VISUALIZATION:",
                visual["technical"],
            ]
        )

    if visual.get("dialogue_pacing"):
        lines.extend(
            [
                "",
                "DIALOGUE PACING:",
                visual["dialogue_pacing"],
            ]
        )

    lines.extend(
        [
            "",
            "AUDIO HANDOFF:",
            "Approved dialogue is delivered downstream with native lip-sync. "
            "Engine-room ambience only. No background music.",
            "",
            "Do not add subtitles, captions, labels, or readable machinery text.",
        ]
    )
    return "\n".join(lines).strip()


def validate_scene_ids(
    script: dict,
    storyboard: dict,
    veo: dict,
) -> list[str]:
    script_ids = [scene["scene_id"] for scene in script.get("scenes", [])]
    board_ids = [scene["scene_id"] for scene in storyboard.get("scenes", [])]
    veo_ids = [scene["scene_id"] for scene in veo.get("scenes", [])]

    if not script_ids:
        raise RuntimeError("script.json contains no scenes.")
    if not (script_ids == board_ids == veo_ids):
        raise RuntimeError(
            "Scene IDs differ between script.json, storyboard.json and "
            "veo_prompts.json."
        )

    missing = [sid for sid in script_ids if sid not in SCENE_VISUALS]
    if missing:
        raise RuntimeError(
            "No Episode 001 quality-first visual definition for: "
            + ", ".join(missing)
        )
    return script_ids


def repair_episode(
    script: dict,
    storyboard: dict,
    veo: dict,
) -> None:
    scene_ids = validate_scene_ids(script, storyboard, veo)
    board_by_id = {
        scene["scene_id"]: scene
        for scene in storyboard["scenes"]
    }
    veo_by_id = {
        scene["scene_id"]: scene
        for scene in veo["scenes"]
    }
    script_by_id = {
        scene["scene_id"]: scene
        for scene in script["scenes"]
    }

    cursor = 0.0
    for sid in scene_ids:
        script_scene = script_by_id[sid]
        visual = SCENE_VISUALS[sid]
        duration = float(PREFERRED_DURATIONS[sid])

        words = word_count(script_scene)
        if words:
            minimum = words / MAX_WORDS_PER_SECOND
            if duration < minimum:
                # Expand only this scene. Never steal time from another scene.
                duration = (int(minimum * 2 + 0.999999)) / 2.0

        script_scene["start_s"] = cursor
        script_scene["end_s"] = cursor + duration
        script_scene["visual_action"] = visual["action"]

        board = board_by_id[sid]
        board["start_s"] = cursor
        board["end_s"] = cursor + duration
        board["camera"] = visual["camera"]
        board["composition"] = visual["composition"]
        board["character_actions"] = [visual["action"]]
        board["technical_visualization"] = visual.get("technical")

        prompt = veo_by_id[sid]
        prompt["duration_s"] = duration
        prompt["prompt"] = build_visual_prompt(
            sid,
            duration,
            visual,
        )
        prompt["negative_prompt"] = clean_negative(
            prompt.get("negative_prompt", "")
        )

        cursor += duration

    script["duration_s"] = cursor
    storyboard["aspect_ratio"] = "9:16"
    veo["aspect_ratio"] = "9:16"


def verify_episode(
    script: dict,
    storyboard: dict,
    veo: dict,
) -> None:
    ids = validate_scene_ids(script, storyboard, veo)
    board_by_id = {
        scene["scene_id"]: scene
        for scene in storyboard["scenes"]
    }
    veo_by_id = {
        scene["scene_id"]: scene
        for scene in veo["scenes"]
    }

    cursor = 0.0
    for scene in script["scenes"]:
        sid = scene["scene_id"]
        start = float(scene["start_s"])
        end = float(scene["end_s"])
        duration = end - start

        if abs(start - cursor) > 0.01:
            raise RuntimeError(
                f"Timeline gap/overlap before {sid}: expected {cursor}, got {start}."
            )
        if duration <= 0:
            raise RuntimeError(f"Invalid duration for {sid}: {duration}")

        words = word_count(scene)
        rate = words / duration if words else 0.0
        if rate > MAX_WORDS_PER_SECOND + 0.01:
            raise RuntimeError(
                f"{sid} dialogue still too tight: {words} words / "
                f"{duration:.1f}s = {rate:.2f} w/s."
            )

        board = board_by_id[sid]
        prompt = veo_by_id[sid]
        board_duration = float(board["end_s"]) - float(board["start_s"])

        if abs(board_duration - duration) > 0.01:
            raise RuntimeError(
                f"Storyboard duration mismatch for {sid}."
            )
        if abs(float(prompt["duration_s"]) - duration) > 0.01:
            raise RuntimeError(
                f"Veo duration mismatch for {sid}."
            )
        if f"Duration {duration:.1f} seconds" not in prompt["prompt"]:
            raise RuntimeError(
                f"Embedded prompt duration mismatch for {sid}."
            )

        lower = (
            str(prompt["prompt"]) + " " + str(prompt["negative_prompt"])
        ).lower()
        if scene.get("dialogue"):
            for conflict in (
                "no spoken dialogue audio",
                "no dialogue audio",
                "lip-sync mouth shapes for spoken words",
            ):
                if conflict in lower:
                    raise RuntimeError(
                        f"Audio conflict remains in {sid}: {conflict}"
                    )

        cursor = end

    if abs(float(script["duration_s"]) - cursor) > 0.01:
        raise RuntimeError(
            "script.duration_s does not match the assembled timeline."
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Quality-first deterministic repair for Episode 001 Flow prompts."
        )
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

    repair_episode(script, storyboard, veo)
    verify_episode(script, storyboard, veo)

    write_json(paths["script"], script)
    write_json(paths["storyboard"], storyboard)
    write_json(paths["veo"], veo)

    review_path = episode_dir / "flow_prompt_review.json"
    if review_path.exists():
        review_path.unlink()

    print(f"Repaired episode   : {args.episode_id}")
    print(f"Soft target        : {SOFT_TARGET_SECONDS:.1f}s")
    print(f"Optimized duration : {script['duration_s']:.1f}s")
    print("Quality-first scene timing:")

    for scene in script["scenes"]:
        duration = float(scene["end_s"]) - float(scene["start_s"])
        words = word_count(scene)
        rate = words / duration if words else 0.0
        print(
            f"  {scene['scene_id']}: {duration:.1f}s, "
            f"{words} words, {rate:.2f} w/s"
        )

    print()
    print("No hard total-duration cap was applied.")
    print("Backups: *.quality_first_backup")
    print("Next: python scripts/review_flow_prompts.py --episode-id "
          f"{args.episode_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())