from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents import content_reviewer
from core.provider_router import ProviderRouter
from core.schemas import (
    EpisodeRequest,
    IdeaOutput,
    ScriptOutput,
    StoryOutput,
)
from core.state_manager import EpisodeStateManager


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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


def latest_reviewable_episode(root: Path) -> str | None:
    required = ("input.json", "idea.json", "story.json", "script.json")

    for episode_id in list_episode_ids(root):
        episode_dir = root / episode_id
        if all((episode_dir / name).exists() for name in required):
            return episode_id

    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Review one Tiny Engine Cadet idea + story + script package."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--episode-id")
    group.add_argument("--latest", action="store_true")
    args = parser.parse_args()

    episodes_root = PROJECT_ROOT / "outputs" / "episodes"
    state = EpisodeStateManager(episodes_root)

    episode_id = (
        latest_reviewable_episode(episodes_root)
        if args.latest
        else args.episode_id
    )

    if not episode_id:
        print("No reviewable episode found.")
        return 1

    try:
        manifest = state.load_manifest(episode_id)
    except FileNotFoundError:
        print(f"Episode not found: {episode_id}")
        recent = list_episode_ids(episodes_root)[:10]
        if recent:
            print("Recent episodes:")
            for item in recent:
                print(f"  {item}")
        return 1

    episode_dir = Path(manifest.output_dir)
    required = {
        "input": episode_dir / "input.json",
        "idea": episode_dir / "idea.json",
        "story": episode_dir / "story.json",
        "script": episode_dir / "script.json",
    }

    missing = [
        name
        for name, path in required.items()
        if not path.exists()
    ]
    if missing:
        print("Episode is not reviewable. Missing: " + ", ".join(missing))
        return 1

    request = EpisodeRequest.model_validate(load_json(required["input"]))
    idea = IdeaOutput.model_validate(load_json(required["idea"]))
    story = StoryOutput.model_validate(load_json(required["story"]))
    script = ScriptOutput.model_validate(load_json(required["script"]))

    llm = ProviderRouter().for_stage("content_review")
    review = content_reviewer.run(
        llm,
        request,
        idea,
        story,
        script,
    )

    report_path = episode_dir / "review_report.json"
    state.write_json(report_path, review.model_dump())
    manifest.files["content_review"] = str(report_path)

    if "content_review" not in manifest.completed_stages:
        manifest.completed_stages.append("content_review")

    if review.decision == "PASS":
        if manifest.status == "needs_content_revision":
            manifest.status = "content_review_passed"
        manifest.error = None
    else:
        manifest.status = "needs_content_revision"
        manifest.current_stage = "content_review"
        manifest.error = None

    state.save_manifest(manifest)

    print(f"Episode  : {episode_id}")
    print(f"Decision : {review.decision}")
    print(f"Score    : {review.overall_score}/100")
    print(f"Report   : {report_path}")
    print()
    print(review.executive_summary)

    if review.issues:
        print("\nTop issues:")
        for issue in review.issues[:5]:
            scene = f" [{issue.scene_id}]" if issue.scene_id else ""
            print(
                f"- {issue.severity.upper()} {issue.category}{scene}: "
                f"{issue.finding}"
            )
            print(f"  Repair: {issue.repair_instruction}")

    return 0 if review.decision == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
