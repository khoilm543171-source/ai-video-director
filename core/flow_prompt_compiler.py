"""Compile approved scene data into independent Flow jobs and downstream metadata.

The spec owns dialogue, duration, spatial continuity and the visual direction.
Generated files are replaced atomically; older planning files get a one-time backup.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from core.flow_preflight import check_flow_spec, require_flow_spec


CHARACTERS = {"tiny_cadet": "Tiny Cadet", "chief_engineer": "Chief Engineer"}


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def _json(path: Path, value: dict[str, Any]) -> None:
    _write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _dialogue(lines: list[dict[str, str]]) -> list[str]:
    if not lines:
        return ["No character speech during this step; preserve ship ambience only."]
    return [f'{CHARACTERS[item["character"]]}: "{item["text"]}"' for item in lines]


def _visual(spec: dict[str, Any], scene: dict[str, Any], phase: str | None = None) -> list[str]:
    g = spec["global"]
    return [
        "REFERENCES: @TinyCadet, @ChiefEngineer, @EngineRoom. Use the SAME three reusable identity/environment assets in every scene.",
        f'STYLE: {g["style"]}',
        f'ROOM: {g["environment"]}',
        f'IDENTITY: {g["tiny_cadet"]} {g["chief_engineer"]}',
        f'PURIFIER: {g["purifier"]}',
        f'GEOGRAPHY: {g["geography"]}',
        f'START STATE: {scene["state_in"]}.',
        f'ACTION: {scene.get("render_steps", {}).get(f"{phase}_action", scene["action"]) if phase else scene["action"]}',
        f'CAMERA: {scene["camera"]}',
        f'COMPOSITION: {scene["composition"]}',
        f'END STATE: {"Hold the same shot for the in-scene extension; do not jump to the next numbered scene." if phase == "base" and scene["duration_s"] > 8 else scene["end_pose"]}',
        f'CONTINUITY: Chief screen-{scene["chief_side"]}; Cadet screen-{scene["cadet_side"]}; fuel screen-left to screen-right; purifier inlet left/outlet right.',
    ]


def _prompt(spec: dict[str, Any], scene: dict[str, Any], *, phase: str | None = None) -> str:
    sid = scene["scene_id"]
    duration = scene["duration_s"]
    parts = [
        f'{sid} — TARGET FINAL CLIP {duration:g} SECONDS. Independent vertical video scene; do not include adjacent scenes or transitions.',
    ]
    if phase:
        parts.append(f'FLOW RENDER STEP: {phase}. Generate an 8-second vertical 9:16 Veo 3.1 Lite clip with the SAME references. The final {duration:g}-second scene is accepted only after in-scene extension/trimming and review.')
    parts.extend(_visual(spec, scene, phase))
    lines = scene["dialogue"]
    if phase:
        lines = scene.get("render_steps", {}).get(f"{phase}_dialogue", scene["dialogue"])
        parts.append("EXTEND THE SAME SCENE only; preserve the last frame, speaker voice, identity, geography and action. Do not jump to another scene." if phase == "extend" else "Start with the stated start pose. Keep enough visual headroom to extend this same scene later.")
    parts.extend([
        f'AUDIO: {spec["global"]["audio"]}',
        f'TIMING: {scene["audio_timing"]}' if not phase else "TIMING: This step contains only the quoted fragment below; preserve pauses and leave a clean in-scene extension/trim boundary.",
        "SPEAK ONLY THESE WORDS IN THIS RENDER STEP (in order):",
        *_dialogue(lines),
        f'AVOID: {spec["global"]["avoid"]}',
        "No one-file full episode. Keep each scene as its own downloadable video file.",
    ])
    return "\n\n".join(parts) + "\n"


def _planning_metadata(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cursor = 0.0
    script, storyboard, veo = [], [], []
    for scene in spec["scenes"]:
        start = cursor
        cursor += scene["duration_s"]
        sid = scene["scene_id"]
        script.append({
            "scene_id": sid, "start_s": start, "end_s": cursor,
            "location": "merchant ship engine room", "purpose": scene["end_pose"],
            "visual_action": scene["action"], "dialogue": [
                {"character": line["character"], "text": line["text"],
                 "emotion": "natural", "delivery": "natural", "start_offset_s": 0.0}
                for line in scene["dialogue"]
            ], "on_screen_text": None,
            "technical_point": scene.get("technical_point"),
        })
        storyboard.append({
            "scene_id": sid, "start_s": start, "end_s": cursor,
            "shot_type": scene["camera"], "camera": scene["camera"],
            "composition": scene["composition"], "character_actions": [scene["action"]],
            "machinery_and_environment": [spec["global"]["environment"], spec["global"]["purifier"]],
            "continuity_from_previous": scene["state_in"], "technical_visualization": scene.get("technical_visualization"),
        })
        veo.append({
            "scene_id": sid, "duration_s": scene["duration_s"],
            "prompt": "\n".join(_visual(spec, scene)) + f'\nDuration {scene["duration_s"]:g} seconds (final scene clip).',
            "negative_prompt": spec["global"]["avoid"],
            "reference_assets": ["assets/characters/tiny_cadet.png", "assets/characters/chief_engineer.png", "assets/environments/engine_room.png"],
        })
    question = spec["interview_question"]
    return {
        "input.json": {"episode_id": spec["episode_id"], "question": question,
                       "answer": spec["technical_truth"], "source_notes": spec["technical_truth"],
                       "target_duration_s": spec["target_duration_s"]},
        "script.json": {"title": spec["title"], "duration_s": cursor, "scenes": script,
                        "final_interview_question": question, "final_interview_answer": spec["technical_truth"]},
        "storyboard.json": {"aspect_ratio": "9:16", "scenes": storyboard},
        "veo_prompts.json": {"aspect_ratio": "9:16", "scenes": veo},
        "context.json": {"series_rules": spec["global"], "characters": {
            "tiny_cadet": spec["global"]["tiny_cadet"], "chief_engineer": spec["global"]["chief_engineer"]},
            "episode_facts": [spec["technical_truth"]],
            "forbidden_visual_errors": [spec["global"]["avoid"]],
            "global_visual_prompt": spec["global"]["style"] + " " + spec["global"]["environment"],
            "negative_prompt": spec["global"]["avoid"]},
    }


def compile_flow_spec(spec: dict[str, Any], episodes_root: Path) -> Path:
    require_flow_spec(spec)
    eid = spec["episode_id"]
    if not eid or Path(eid).name != eid or eid in {".", ".."}:
        raise ValueError("Unsafe episode_id.")
    root = episodes_root / eid
    flow = root / "flow_jobs"
    flow.mkdir(parents=True, exist_ok=True)

    metadata = _planning_metadata(spec)
    backups = flow / "previous_planning"
    previous_manifest_path = root / "manifest.json"
    previous_manifest = json.loads(previous_manifest_path.read_text(encoding="utf-8")) if previous_manifest_path.exists() else None
    metadata_changed = any(
        (root / filename).exists() and
        (root / filename).read_text(encoding="utf-8") != json.dumps(content, ensure_ascii=False, indent=2) + "\n"
        for filename, content in metadata.items()
    )
    for old_name in ("manifest.json", "flow_prompt_review.json"):
        old = root / old_name
        archived = backups / old_name
        if old.exists():
            if not archived.exists():
                _write(archived, old.read_text(encoding="utf-8"))
            if old_name == "flow_prompt_review.json":
                old.unlink()  # Old LLM score refers to the superseded planning data.
    for filename, content in metadata.items():
        path = root / filename
        if path.exists():
            current = path.read_text(encoding="utf-8")
            replacement = json.dumps(content, ensure_ascii=False, indent=2) + "\n"
            if current != replacement and not (backups / filename).exists():
                _write(backups / filename, current)
        _json(path, content)

    jobs = []
    batch = [
        f'GOOGLE FLOW AGENT — {spec["title"]}',
        f'Create EXACTLY {spec["expected_clips"]} separate FINAL vertical 9:16 files, scene_01 through scene_{len(spec["scenes"]):02d}.',
        "Each numbered scene is a separate production job. Do not merge or crossfade BETWEEN scenes; do not create one long movie.",
        "For scenes longer than a supported native duration, extend WITHIN that scene and export exactly one final file for that scene.",
        f'Final assembled runtime: {sum(s["duration_s"] for s in spec["scenes"]):g} seconds. Do not add subtitles, text, music or extra dialogue.',
        f'GLOBAL IDENTITY: {spec["global"]["tiny_cadet"]} {spec["global"]["chief_engineer"]}',
        f'GLOBAL SET: {spec["global"]["environment"]}',
    ]
    timeline = 0.0
    for scene in spec["scenes"]:
        sid = scene["scene_id"]
        duration = scene["duration_s"]
        _write(flow / f"{sid}.txt", _prompt(spec, scene))
        steps = [
            {"kind": "base", "prompt_file": f"{sid}_base.txt", "requested_native_s": 8,
             "dialogue": scene["render_steps"]["base_dialogue"]}
        ] if duration > 8 else [
            {"kind": "base", "prompt_file": f"{sid}_base.txt", "requested_native_s": 8,
             "dialogue": scene["dialogue"]}
        ]
        _write(flow / steps[0]["prompt_file"], _prompt(spec, scene, phase="base"))
        if duration > 8:
            steps.append({"kind": "extend", "prompt_file": f"{sid}_extend.txt", "requested_native_s": 8,
                          "dialogue": scene["render_steps"]["extend_dialogue"]})
            _write(flow / f"{sid}_extend.txt", _prompt(spec, scene, phase="extend"))
        job = {
            "scene_id": sid, "duration_s": duration, "start_s": timeline,
            "end_s": timeline + duration, "prompt_file": f"{sid}.txt",
            "expected_video": f"scenes/{sid}.mp4", "render_steps": steps,
            "reference_assets": ["TinyCadet", "ChiefEngineer", "EngineRoom"],
            "dialogue": scene["dialogue"], "state_in": scene["state_in"],
            "state_out": scene["state_out"],
        }
        timeline += duration
        jobs.append(job)
        batch.extend([f'\n===== {sid} — {duration:g} SECONDS; ONE FINAL FILE =====',
                      _prompt(spec, scene)])

    reference_config = json.loads((Path(__file__).resolve().parents[1] / "config" / "reference_asset_prompts.json").read_text(encoding="utf-8"))
    references = []
    for name, asset in reference_config["assets"].items():
        filename = f"reference_{name}.txt"
        _write(flow / filename, asset["prompt"] + "\n\nAVOID: " + asset["avoid"] + "\n")
        references.append(filename)
    _write(flow / "FLOW_BATCH_PROMPT.txt", "\n\n".join(batch) + "\n")
    _json(flow / "flow_jobs.json", {"episode_id": eid, "expected_final_clips": len(jobs),
                                     "total_duration_s": timeline, "jobs": jobs})
    _json(root / "flow_prompt_preflight.json", {"render_gate": "PASS", "blocking_issues": check_flow_spec(spec),
                                                 "source": "structured_episode_spec", "total_duration_s": timeline})
    start_here_text = "\n".join([
        f"# {spec['title']} — eight separate scene files",
        "", "Create the same three reusable reference assets once:",
        *(f"- {name}" for name in references), "",
        "Generate one scene job at a time. Use its scene_XX_base.txt with the three references.",
        "Flow Veo 3.1 Ingredients/References generates 8s clips; longer scenes need scene_XX_extend.txt with Veo 3.1 Lite, extending the SAME scene.",
        "For short scenes, trim only silence/tail to the locked duration. For long scenes, extend and trim the tail only after the final word and action.",
        "Keep each final video separate: scenes/scene_01.mp4 through scenes/scene_08.mp4. No transitions or crossfades.",
        "Verify actual duration and vertical ratio with scripts/check_flow_clips.py. Listen to every line and inspect lip sync and cross-scene handoffs before using videos.",
        "If a render cuts a word, changes a voice or flips geography, regenerate that scene. Never trim spoken words to meet timing.",
        "No API key is needed for this offline pack. FLOW_BATCH_PROMPT.txt is a production brief; do not paste it as one single-video prompt.", "",
    ])
    _write(flow / "START_HERE.md", start_here_text)
    _write(flow / "REFERENCE_SETUP.md", start_here_text)
    old_status = previous_manifest.get("status") if previous_manifest else None
    has_rendered_scenes = any((root / "scenes").glob("scene_*.mp4"))
    new_status = "needs_scene_review" if metadata_changed and has_rendered_scenes else (
        old_status if old_status in {"video_scenes_rendered", "rendering_partial", "needs_scene_review"} and not metadata_changed
        else "ready_for_render"
    )
    manifest_files = previous_manifest.get("files", {}) if previous_manifest else {}
    manifest_files.update({name.removesuffix(".json"): str((root / name).resolve()) for name in metadata})
    _json(root / "manifest.json", {
        "episode_id": eid, "status": new_status, "question": metadata["input.json"]["question"],
        "output_dir": str(root.resolve()),
        "completed_stages": list(dict.fromkeys([
            *(previous_manifest.get("completed_stages", []) if previous_manifest else []),
            "input", "script", "storyboard", "context", "veo_prompts", "flow_prompt_preflight"])),
        "current_stage": None, "files": manifest_files,
        "error": None,
    })
    return flow
