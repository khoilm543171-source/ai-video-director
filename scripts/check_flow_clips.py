"""Verify the eight downloaded scene files before any later assembly."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def inspect_clips(plan: dict, scenes_dir: Path) -> list[str]:
    errors: list[str] = []
    expected = {f'{job["scene_id"]}.mp4' for job in plan["jobs"]}
    actual = {p.name for p in scenes_dir.glob("scene_*.mp4")}
    for missing in sorted(expected - actual):
        errors.append(f"Missing final scene file: {missing}")
    for extra in sorted(actual - expected):
        errors.append(f"Unexpected scene file: {extra}")

    for job in plan["jobs"]:
        path = scenes_dir / f'{job["scene_id"]}.mp4'
        if not path.is_file():
            continue
        try:
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries",
                 "format=duration:stream=codec_type,width,height", "-of", "json", str(path)],
                capture_output=True, text=True, timeout=30,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            errors.append(f"Cannot inspect {path.name}: ffprobe unavailable/timed out ({exc}).")
            continue
        if probe.returncode:
            errors.append(f"Cannot read {path.name}: {probe.stderr.strip()[:160]}")
            continue
        try:
            data = json.loads(probe.stdout)
            actual_duration = float(data["format"]["duration"])
            video = next(stream for stream in data["streams"] if stream["codec_type"] == "video")
            width, height = int(video["width"]), int(video["height"])
        except (ValueError, KeyError, StopIteration, TypeError) as exc:
            errors.append(f"Invalid video metadata in {path.name}: {exc}")
            continue
        if abs(actual_duration - job["duration_s"]) > 0.06:
            errors.append(f'{path.name}: {actual_duration:.3f}s, expected {job["duration_s"]:g}s.')
        if width <= 0 or height <= 0 or abs(width / height - 9 / 16) > 0.012:
            errors.append(f"{path.name}: {width}x{height} is not native vertical 9:16.")
        if not any(stream.get("codec_type") == "audio" for stream in data["streams"]):
            errors.append(f"{path.name}: missing native audio stream.")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate final Google Flow scene downloads.")
    parser.add_argument("--episode-id", default="episode_001_fuel_oil_purifier")
    args = parser.parse_args()
    root = PROJECT_ROOT / "outputs" / "episodes" / args.episode_id
    plan_file = root / "flow_jobs" / "flow_jobs.json"
    if not plan_file.is_file():
        print("Flow pack is missing. First run build_flow_pack.py.")
        return 2
    plan = json.loads(plan_file.read_text(encoding="utf-8"))
    errors = inspect_clips(plan, root / "scenes")
    if errors:
        print("Video preflight BLOCK:")
        for error in errors:
            print(f"- {error}")
        return 2
    print(f"Video metadata PASS: {len(plan['jobs'])} distinct vertical scene files, {plan['total_duration_s']:g}s total.")
    print("Human QA still required: exact words, voices, lip-sync, purifier meaning and scene-to-scene continuity.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
