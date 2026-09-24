from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.visual_reviewer import GeminiVisualReviewer
from core.state_manager import EpisodeStateManager


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def list_episode_ids(root: Path) -> list[str]:
    if not root.exists():
        return []
    items = [
        p for p in root.iterdir()
        if p.is_dir() and (p / "manifest.json").exists()
    ]
    items.sort(
        key=lambda p: (p / "manifest.json").stat().st_mtime,
        reverse=True,
    )
    return [p.name for p in items]


def latest_episode_with_scene(root: Path, scene_id: str) -> str | None:
    for episode_id in list_episode_ids(root):
        episode_dir = root / episode_id
        if (
            (episode_dir / "script.json").exists()
            and (episode_dir / "storyboard.json").exists()
            and (episode_dir / "context.json").exists()
            and (episode_dir / "scenes" / f"{scene_id}.mp4").exists()
        ):
            return episode_id
    return None


def find_scene(items: list[dict], scene_id: str) -> dict:
    for item in items:
        if item.get("scene_id") == scene_id:
            return item
    raise ValueError(f"Scene not found in metadata: {scene_id}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Multimodal review of one rendered Tiny Engine Cadet scene."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--episode-id")
    group.add_argument("--latest", action="store_true")
    parser.add_argument("--scene", default="scene_01")
    args = parser.parse_args()

    episodes_root = PROJECT_ROOT / "outputs" / "episodes"
    state = EpisodeStateManager(episodes_root)

    episode_id = (
        latest_episode_with_scene(episodes_root, args.scene)
        if args.latest
        else args.episode_id
    )
    if not episode_id:
        print(f"No episode with {args.scene}.mp4 was found.")
        return 1

    manifest = state.load_manifest(episode_id)
    episode_dir = Path(manifest.output_dir)

    script = load_json(episode_dir / "script.json")
    storyboard = load_json(episode_dir / "storyboard.json")
    context = load_json(episode_dir / "context.json")

    character_bible = load_json(
        PROJECT_ROOT / "config" / "character_bible.json"
    )
    environment_bible = load_json(
        PROJECT_ROOT / "config" / "environment_bible.json"
    )

    script_scene = find_scene(script["scenes"], args.scene)
    storyboard_scene = find_scene(storyboard["scenes"], args.scene)
    video_path = episode_dir / "scenes" / f"{args.scene}.mp4"

    reviewer = GeminiVisualReviewer()
    review = reviewer.review_scene(
        scene_id=args.scene,
        video_path=video_path,
        script_scene=script_scene,
        storyboard_scene=storyboard_scene,
        episode_facts=context.get("episode_facts", []),
        character_rules=character_bible,
        environment_rules=environment_bible,
    )

    out_dir = episode_dir / "visual_reviews"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.scene}.json"
    state.write_json(out_path, review.model_dump())

    print(f"Episode  : {episode_id}")
    print(f"Scene    : {args.scene}")
    print(f"Decision : {review.decision}")
    print(f"Score    : {review.overall_score}/100")
    print(f"Confidence: {review.confidence:.2f}")
    print(f"Report   : {out_path}")
    print()
    print(review.summary)

    if review.issues:
        print("\nIssues:")
        for issue in review.issues:
            t = (
                f" @{issue.time_hint_s:.1f}s"
                if issue.time_hint_s is not None
                else ""
            )
            print(
                f"- {issue.severity.upper()} "
                f"{issue.category}{t}: {issue.finding}"
            )
            print(f"  Repair: {issue.repair_instruction}")

    if review.decision == "RETRY_SCENE" and review.retry_prompt_delta:
        print("\nRetry prompt delta:")
        print(review.retry_prompt_delta)

    return 0 if review.decision == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
