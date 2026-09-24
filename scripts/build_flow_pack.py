from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.state_manager import EpisodeStateManager


ASSET_RULES = {
    "tiny_cadet": (
        "@TinyCadet is the exact recurring identity reference. Preserve the "
        "same face, white safety helmet, navy-blue cadet coverall, black "
        "safety shoes and miniature body proportions."
    ),
    "chief_engineer": (
        "@ChiefEngineer is the exact recurring identity reference. Preserve "
        "the same face, white safety helmet, dark navy coverall, black "
        "safety shoes and slightly taller mentor proportions."
    ),
    "engine_room": (
        "@EngineRoom is the recurring environment reference. Preserve the "
        "same merchant-ship engine-room visual language, machinery scale, "
        "walkways, pipes, handrails, palette and practical industrial lighting."
    ),
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def detect_characters(scene: dict) -> list[str]:
    found: list[str] = []

    for line in scene.get("dialogue", []):
        character = line.get("character")
        if character in {"tiny_cadet", "chief_engineer"}:
            found.append(character)

    haystack = " ".join(
        [
            str(scene.get("visual_action") or ""),
            str(scene.get("purpose") or ""),
            str(scene.get("technical_point") or ""),
        ]
    ).lower()

    if "cadet" in haystack:
        found.append("tiny_cadet")
    if "chief" in haystack or "engineer" in haystack:
        found.append("chief_engineer")

    return list(dict.fromkeys(found))


def build_scene_prompt(
    scene_prompt: dict,
    script_scene: dict,
) -> str:
    characters = detect_characters(script_scene)

    reference_lines = [ASSET_RULES["engine_room"]]
    if "tiny_cadet" in characters:
        reference_lines.append(ASSET_RULES["tiny_cadet"])
    if "chief_engineer" in characters:
        reference_lines.append(ASSET_RULES["chief_engineer"])

    duration = scene_prompt.get("duration_s")
    core_prompt = scene_prompt["prompt"].strip()
    negative = scene_prompt.get("negative_prompt", "").strip()

    lines = [
        "FLOW / VEO SCENE PROMPT",
        "",
        "REFERENCES / INGREDIENTS:",
        *[f"- {line}" for line in reference_lines],
        "",
        "SHOT:",
        core_prompt,
        "",
        f"Target duration: {duration} seconds.",
        "Native vertical 9:16 composition.",
        "No subtitles or baked-in text.",
    ]

    if negative:
        lines.extend(
            [
                "",
                "AVOID:",
                negative,
            ]
        )

    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build manual Google Flow prompt pack for one episode."
    )
    parser.add_argument("--episode-id", required=True)
    args = parser.parse_args()

    state = EpisodeStateManager(PROJECT_ROOT / "outputs" / "episodes")
    manifest = state.load_manifest(args.episode_id)
    episode_dir = Path(manifest.output_dir)

    script_path = episode_dir / "script.json"
    veo_path = episode_dir / "veo_prompts.json"

    if not script_path.exists() or not veo_path.exists():
        raise FileNotFoundError(
            "script.json or veo_prompts.json is missing. "
            "Run the episode planning pipeline first."
        )

    script_data = load_json(script_path)
    veo_data = load_json(veo_path)

    script_by_id = {
        scene["scene_id"]: scene
        for scene in script_data.get("scenes", [])
    }

    flow_dir = episode_dir / "flow_jobs"
    flow_dir.mkdir(parents=True, exist_ok=True)

    index = []

    for scene_prompt in veo_data.get("scenes", []):
        scene_id = scene_prompt["scene_id"]
        script_scene = script_by_id.get(scene_id, {})

        text = build_scene_prompt(
            scene_prompt,
            script_scene,
        )

        path = flow_dir / f"{scene_id}.txt"
        path.write_text(text, encoding="utf-8")

        index.append(
            {
                "scene_id": scene_id,
                "prompt_file": str(path),
                "expected_video": str(
                    episode_dir / "scenes" / f"{scene_id}.mp4"
                ),
                "references": [
                    "EngineRoom",
                    *(
                        ["TinyCadet"]
                        if "tiny_cadet" in detect_characters(script_scene)
                        else []
                    ),
                    *(
                        ["ChiefEngineer"]
                        if "chief_engineer" in detect_characters(script_scene)
                        else []
                    ),
                ],
            }
        )

    reference_config = load_json(
        PROJECT_ROOT / "config" / "reference_asset_prompts.json"
    )

    setup_lines = [
        "# Flow reference setup",
        "",
        "Create these reusable assets once in the same Flow project.",
        "After generation, name them exactly as shown.",
        "",
    ]

    for asset_name, asset in reference_config["assets"].items():
        setup_lines.extend(
            [
                f"## {asset_name}",
                "",
                asset["prompt"],
                "",
                f"Avoid: {asset['avoid']}",
                "",
            ]
        )

    (flow_dir / "REFERENCE_SETUP.md").write_text(
        "\n".join(setup_lines),
        encoding="utf-8",
    )

    (flow_dir / "flow_jobs.json").write_text(
        json.dumps(
            {
                "episode_id": args.episode_id,
                "flow_assets": [
                    "TinyCadet",
                    "ChiefEngineer",
                    "EngineRoom",
                ],
                "jobs": index,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Flow prompt pack created: {flow_dir}")
    print(f"Scenes: {len(index)}")
    print("Create references from REFERENCE_SETUP.md once, then use scene_*.txt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
