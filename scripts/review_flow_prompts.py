from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents import flow_prompt_reviewer
from core.provider_router import ProviderRouter
from core.schemas import (
    ContextOutput,
    EpisodeRequest,
    ScriptOutput,
    StoryboardOutput,
    VeoPromptsOutput,
)
from core.state_manager import EpisodeStateManager


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Review all Flow/Veo prompts before batch generation."
    )
    parser.add_argument("--episode-id", required=True)
    args = parser.parse_args()

    root = PROJECT_ROOT / "outputs" / "episodes"
    state = EpisodeStateManager(root)
    manifest = state.load_manifest(args.episode_id)
    episode_dir = Path(manifest.output_dir)

    required = {
        "input": episode_dir / "input.json",
        "script": episode_dir / "script.json",
        "storyboard": episode_dir / "storyboard.json",
        "context": episode_dir / "context.json",
        "veo_prompts": episode_dir / "veo_prompts.json",
    }
    missing = [name for name, path in required.items() if not path.exists()]
    if missing:
        print("Missing required files: " + ", ".join(missing))
        return 1

    request = EpisodeRequest.model_validate(load_json(required["input"]))
    script = ScriptOutput.model_validate(load_json(required["script"]))
    storyboard = StoryboardOutput.model_validate(
        load_json(required["storyboard"])
    )
    context = ContextOutput.model_validate(load_json(required["context"]))
    veo_prompts = VeoPromptsOutput.model_validate(
        load_json(required["veo_prompts"])
    )

    review = flow_prompt_reviewer.run(
        ProviderRouter().for_stage("flow_prompt_review"),
        request,
        script,
        storyboard,
        context,
        veo_prompts,
    )

    out = episode_dir / "flow_prompt_review.json"
    state.write_json(out, review.model_dump())

    if review.decision == "PASS":
        manifest.status = "flow_prompt_review_passed"
        manifest.current_stage = "flow_prompt_review"
    else:
        manifest.status = "needs_flow_prompt_revision"
        manifest.current_stage = "flow_prompt_review"
    manifest.files["flow_prompt_review"] = str(out)
    if "flow_prompt_review" not in manifest.completed_stages:
        manifest.completed_stages.append("flow_prompt_review")
    manifest.error = None
    state.save_manifest(manifest)

    print(f"Episode  : {args.episode_id}")
    print(f"Decision : {review.decision}")
    print(f"Score    : {review.overall_score}/100")
    print(f"Report   : {out}")
    print()
    print(review.executive_summary)

    for scene in review.scene_reviews:
        print(
            f"- {scene.scene_id}: {scene.decision} "
            f"{scene.score}/100 — {scene.summary}"
        )
        for issue in scene.issues[:3]:
            print(
                f"    {issue.severity.upper()} {issue.category}: "
                f"{issue.finding}"
            )
            print(f"    Repair: {issue.repair_instruction}")

    if review.cross_scene_issues:
        print("\nCross-scene issues:")
        for issue in review.cross_scene_issues[:5]:
            print(
                f"- {issue.severity.upper()} {issue.category}: "
                f"{issue.finding}"
            )
            print(f"  Repair: {issue.repair_instruction}")

    return 0 if review.decision == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
