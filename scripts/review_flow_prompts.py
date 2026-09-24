from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents import flow_prompt_reviewer
from core.flow_prompt_checks import run_flow_prompt_checks
from core.flow_preflight import check_flow_spec
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

    if args.episode_id == "episode_001_fuel_oil_purifier":
        spec = load_json(PROJECT_ROOT / "examples" / "episode_001_flow.json")
        issues = check_flow_spec(spec)
        print(f"Episode: {args.episode_id}")
        print(f"Deterministic render gate: {'BLOCK' if issues else 'PASS'}")
        for item in issues:
            print(f"- {item['scene_id'] or 'episode'}: {item['finding']}")
        print("LLM score is advisory and not needed to compile the approved spec.")
        return 2 if issues else 0

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

    deterministic_issues = run_flow_prompt_checks(
        script=script.model_dump(),
        storyboard=storyboard.model_dump(),
        veo_prompts=veo_prompts.model_dump(),
    )
    deterministic_blockers = [
        item
        for item in deterministic_issues
        if item.get("severity") in {"high", "critical"}
    ]
    render_gate = "BLOCK" if deterministic_blockers else "PASS"

    review = None
    advisory_error = None
    if render_gate == "PASS":
        try:
            review = flow_prompt_reviewer.run(
                ProviderRouter().for_stage("flow_prompt_review"),
                request,
                script,
                storyboard,
                context,
                veo_prompts,
            )
        except Exception as exc:
            advisory_error = f"{type(exc).__name__}: {exc}"

    out = episode_dir / "flow_prompt_review.json"
    if review is not None:
        state.write_json(out, review.model_dump())

    preflight_out = episode_dir / "flow_prompt_preflight.json"
    state.write_json(
        preflight_out,
        {
            "render_gate": render_gate,
            "blocking_issues": deterministic_blockers,
            "all_deterministic_issues": deterministic_issues,
            "llm_review_decision": review.decision if review else None,
            "llm_review_score": review.overall_score if review else None,
            "llm_review_error": advisory_error,
        },
    )

    manifest.status = (
        "flow_prompt_preflight_passed"
        if render_gate == "PASS"
        else "needs_flow_prompt_revision"
    )
    manifest.current_stage = "flow_prompt_review"
    if review is not None:
        manifest.files["flow_prompt_review"] = str(out)
    manifest.files["flow_prompt_preflight"] = str(preflight_out)
    if "flow_prompt_review" not in manifest.completed_stages:
        manifest.completed_stages.append("flow_prompt_review")
    manifest.error = None
    state.save_manifest(manifest)

    print(f"Episode  : {args.episode_id}")
    print(f"Render gate : {render_gate}")
    print(f"LLM review  : {review.decision if review else 'unavailable (advisory)'}")
    print(f"LLM score   : {str(review.overall_score) + '/100' if review else 'n/a'}")
    print(f"Report      : {out}")
    print(f"Preflight   : {preflight_out}")
    print()
    if review is None:
        print(advisory_error or "Deterministic issues blocked advisory review.")
        return 0 if render_gate == "PASS" else 2

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

    if deterministic_blockers:
        print("\nDeterministic blockers:")
        for issue in deterministic_blockers:
            print(
                f"- {str(issue.get('severity')).upper()} "
                f"{issue.get('category')}: {issue.get('finding')}"
            )
    else:
        print(
            "\nRender gate PASS: LLM score is advisory and does not block "
            "Flow packaging."
        )

    return 0 if render_gate == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
