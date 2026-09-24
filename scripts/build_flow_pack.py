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

CHARACTER_LABELS = {
    "tiny_cadet": "Tiny Cadet",
    "chief_engineer": "Chief Engineer",
    "narrator": "Narrator",
}


def clean_core_prompt(value: str) -> str:
    text = value.strip()
    for phrase in (
        "No spoken dialogue audio.",
        "No dialogue audio.",
        "No spoken audio.",
    ):
        text = text.replace(phrase, "")
    return " ".join(text.split())


def clean_negative_prompt(value: str) -> str:
    remove = {
        "dialogue audio",
        "speech",
        "vocals",
        "lip-sync mouth shapes for spoken words",
    }
    parts = [part.strip() for part in value.split(",") if part.strip()]
    return ", ".join(part for part in parts if part.lower() not in remove)


def dialogue_block(script_scene: dict) -> list[str]:
    dialogue = script_scene.get("dialogue", [])
    if not dialogue:
        return [
            "No spoken dialogue in this scene.",
            "Generate only subtle synchronized engine-room ambience; no music.",
        ]

    lines = [
        "Generate native synchronized dialogue audio with natural lip-sync.",
        "Use the exact approved words below. Do not paraphrase, add filler, or invent narration.",
        "Keep each recurring character's voice identity consistent across scenes.",
        "Keep engine-room ambience subtle under speech. No background music.",
        "",
    ]
    for item in dialogue:
        character = item.get("character", "narrator")
        label = CHARACTER_LABELS.get(character, character)
        spoken = str(item.get("text") or "").strip()
        emotion = str(item.get("emotion") or "neutral").strip()
        delivery = str(item.get("delivery") or "natural").strip()
        if spoken:
            lines.append(
                f'- {label} [{emotion}; {delivery}]: "{spoken}"'
            )
    return lines


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
    core_prompt = clean_core_prompt(scene_prompt["prompt"])
    negative = clean_negative_prompt(
        scene_prompt.get("negative_prompt", "")
    )

    lines = [
        "FLOW / VEO SCENE PROMPT",
        "",
        "REFERENCES / INGREDIENTS:",
        *[f"- {line}" for line in reference_lines],
        "",
        "VIDEO:",
        core_prompt,
        "",
        "DIALOGUE / NATIVE AUDIO:",
        *dialogue_block(script_scene),
        "",
        "OUTPUT:",
        f"- Target duration: {duration} seconds.",
        "- Native vertical 9:16 composition.",
        "- One video output for the calibration pass.",
        "- No subtitles, captions, or baked-in text.",
        "- No background music.",
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


def list_episode_ids(root: Path) -> list[str]:
    if not root.exists():
        return []
    items = [
        path
        for path in root.iterdir()
        if path.is_dir() and (path / "manifest.json").exists()
    ]
    items.sort(
        key=lambda path: (path / "manifest.json").stat().st_mtime,
        reverse=True,
    )
    return [path.name for path in items]


def latest_render_ready_episode(root: Path) -> str | None:
    for episode_id in list_episode_ids(root):
        episode_dir = root / episode_id
        if (
            (episode_dir / "script.json").exists()
            and (episode_dir / "veo_prompts.json").exists()
        ):
            return episode_id
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build manual Google Flow prompt pack for one episode."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--episode-id",
        help="Real episode id, for example ep_20260925_001234_ab12cd.",
    )
    group.add_argument(
        "--latest",
        action="store_true",
        help="Use the newest episode that already has script.json and veo_prompts.json.",
    )
    args = parser.parse_args()

    episodes_root = PROJECT_ROOT / "outputs" / "episodes"
    state = EpisodeStateManager(episodes_root)

    if args.latest:
        episode_id = latest_render_ready_episode(episodes_root)
        if not episode_id:
            print("No render-ready episode was found.")
            print(
                "Run: python scripts/run_episode.py "
                "--input examples/episode_request.json"
            )
            return 1
    else:
        episode_id = args.episode_id

    try:
        manifest = state.load_manifest(episode_id)
    except FileNotFoundError:
        print(f"Episode not found: {episode_id}")
        available = list_episode_ids(episodes_root)[:10]
        if available:
            print("\nRecent episode IDs:")
            for item in available:
                print(f"  {item}")
            print("\nTip: use --latest to pick the newest render-ready episode.")
        else:
            print("\nNo episodes exist yet.")
            print(
                "Run: python scripts/run_episode.py "
                "--input examples/episode_request.json"
            )
        return 1

    episode_dir = Path(manifest.output_dir)

    script_path = episode_dir / "script.json"
    veo_path = episode_dir / "veo_prompts.json"

    if not script_path.exists() or not veo_path.exists():
        print(f"Episode {episode_id} is not ready for Flow packaging.")
        print(f"Current status: {manifest.status}")
        print(f"script.json      : {'OK' if script_path.exists() else 'MISSING'}")
        print(f"veo_prompts.json : {'OK' if veo_path.exists() else 'MISSING'}")
        print(
            "\nFinish the planning pipeline first, then run "
            "build_flow_pack.py again."
        )
        return 1

    script_data = load_json(script_path)
    veo_data = load_json(veo_path)

    veo_scenes = veo_data.get("scenes", [])
    print(f"Veo prompt source: {veo_path}")
    print(f"Veo scenes found : {len(veo_scenes)}")
    if not veo_scenes:
        raise RuntimeError(
            "veo_prompts.json contains no scenes. "
            "Re-run the planning pipeline."
        )

    for item in veo_scenes:
        sid = item.get("scene_id", "<missing>")
        prompt_value = item.get("prompt")
        print(
            f"  source {sid}: prompt_type={type(prompt_value).__name__}, "
            f"prompt_len={len(prompt_value) if isinstance(prompt_value, str) else 'n/a'}"
        )

    script_by_id = {
        scene["scene_id"]: scene
        for scene in script_data.get("scenes", [])
    }

    flow_dir = episode_dir / "flow_jobs"
    flow_dir.mkdir(parents=True, exist_ok=True)

    index = []

    # Remove stale generated scene prompt files from older naming schemes.
    for stale in flow_dir.glob("scene_*.txt"):
        stale.unlink()

    for scene_number, scene_prompt in enumerate(veo_data.get("scenes", []), start=1):
        source_scene_id = scene_prompt["scene_id"]
        scene_id = f"scene_{scene_number:02d}"
        script_scene = script_by_id.get(source_scene_id, {})

        scene_text = build_scene_prompt(
            scene_prompt,
            script_scene,
        )

        if not scene_text or not scene_text.strip():
            raise RuntimeError(
                f"Generated empty Flow prompt for {scene_id}. "
                "Check veo_prompts.json and build_scene_prompt()."
            )

        path = flow_dir / f"{scene_id}.txt"
        written = path.write_text(scene_text, encoding="utf-8")

        actual_size = path.stat().st_size if path.exists() else 0
        if written <= 0 or actual_size <= 0:
            raise RuntimeError(
                f"Failed to write non-empty Flow prompt for {scene_id}: "
                f"write_text returned {written}, file size is {actual_size}."
            )

        print(
            f"  wrote {scene_id}: "
            f"{written} chars, {actual_size} bytes -> {path.name}"
        )

        index.append(
            {
                "scene_id": scene_id,
                "source_scene_id": source_scene_id,
                "prompt_file": str(path),
                "expected_video": str(
                    episode_dir / "scenes" / f"{scene_id}.mp4"
                ),
                "dialogue": script_scene.get("dialogue", []),
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

    reference_files = []
    for idx, (asset_name, asset) in enumerate(
        reference_config["assets"].items(),
        start=1,
    ):
        filename = f"reference_{idx:02d}_{asset_name}.txt"
        reference_text = (
            f"FLOW REFERENCE ASSET: {asset_name}\n\n"
            f"{asset['prompt']}\n\n"
            f"AVOID:\n{asset['avoid']}\n"
        )
        (flow_dir / filename).write_text(
            reference_text,
            encoding="utf-8",
        )
        reference_files.append((asset_name, filename))

    setup_lines = [
        "# Google Flow — START HERE",
        "",
        "This folder is the complete manual Flow handoff. Do not rewrite prompts by hand.",
        "",
        "## One-time reference setup",
        "Create these three reusable image assets once in the same Flow project:",
    ]
    for asset_name, filename in reference_files:
        setup_lines.append(
            f"- {asset_name}: copy-paste the full contents of {filename}"
        )

    setup_lines.extend(
        [
            "",
            "Name the resulting assets exactly: TinyCadet, ChiefEngineer, EngineRoom.",
            "",
            "## Render scene_01",
            "1. Open the Flow project on desktop.",
            "2. Go to Scenes / Cảnh.",
            "3. Add/select the references named in scene_01.txt using @ references or ingredients.",
            "4. Paste the full contents of scene_01.txt into the prompt box.",
            "5. Select vertical 9:16, one output, and a compatible video model.",
            "6. Generate only scene_01 for calibration.",
            "7. Download it as scenes/scene_01.mp4.",
            "8. Run the Visual Reviewer before scenes 02-08.",
            "",
            "Each scene prompt already includes exact approved dialogue when dialogue exists.",
            "Do not manually paraphrase or add lines in Flow.",
        ]
    )

    start_here = "\n".join(setup_lines) + "\n"
    (flow_dir / "START_HERE.md").write_text(
        start_here,
        encoding="utf-8",
    )
    (flow_dir / "REFERENCE_SETUP.md").write_text(
        start_here,
        encoding="utf-8",
    )

    (flow_dir / "flow_jobs.json").write_text(
        json.dumps(
            {
                "episode_id": episode_id,
                "native_dialogue_audio": True,
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
    print("Open START_HERE.md, create the 3 references once, then render scene_01.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())