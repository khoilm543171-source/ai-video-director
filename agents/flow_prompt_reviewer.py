from __future__ import annotations

from core.agent_runtime import run_typed_agent
from core.flow_prompt_checks import run_flow_prompt_checks
from core.llm_client import OpenAICompatibleLLM
from core.schemas import (
    ContextOutput,
    EpisodeRequest,
    FlowPromptReviewOutput,
    ScriptOutput,
    StoryboardOutput,
    VeoPromptsOutput,
)
from core.skill_loader import compose_skills


SYSTEM_PROMPT = """
You are the Flow Prompt QA Reviewer for Tiny Engine Cadet.

Review only the supplied scene chunk before Google Flow batch generation.

Rules:
- request.answer, request.source_notes and episode_facts are the technical truth.
- Never silently add outside maritime facts.
- Compare approved script intent/dialogue, storyboard camera/continuity, and final video prompt.
- Dialogue must be exact and realistically fit scene duration.
- The downstream Flow compiler removes legacy audio-suppression phrases and appends exact approved dialogue with native lip-sync.
- Camera instructions must be coherent for vertical 9:16.
- References and continuity must remain stable across scenes.
- Use boundary_context only to judge continuity into/out of this chunk.
- Treat deterministic_checks as mandatory evidence; high/critical findings block PASS.
- PASS only when every supplied scene is batch-safe and no high/critical issue exists.
""" + "\n\n" + compose_skills("flow-prompt-review")


def _compact_scene_payload(
    script: ScriptOutput,
    storyboard: StoryboardOutput,
    veo_prompts: VeoPromptsOutput,
) -> list[dict]:
    board_by_id = {scene.scene_id: scene for scene in storyboard.scenes}
    prompt_by_id = {scene.scene_id: scene for scene in veo_prompts.scenes}

    scenes: list[dict] = []
    for scene in script.scenes:
        board = board_by_id[scene.scene_id]
        prompt = prompt_by_id[scene.scene_id]

        scenes.append(
            {
                "scene_id": scene.scene_id,
                "timing": [scene.start_s, scene.end_s],
                "purpose": scene.purpose,
                "visual_action": scene.visual_action,
                "dialogue": [
                    {
                        "character": line.character,
                        "text": line.text,
                        "emotion": line.emotion,
                        "delivery": line.delivery,
                    }
                    for line in scene.dialogue
                ],
                "technical_point": scene.technical_point,
                "storyboard": {
                    "shot_type": board.shot_type,
                    "camera": board.camera,
                    "composition": board.composition,
                    "continuity": board.continuity_from_previous,
                    "technical_visualization": board.technical_visualization,
                },
                "flow_prompt": {
                    "duration_s": prompt.duration_s,
                    "prompt": prompt.prompt,
                    "negative_prompt": prompt.negative_prompt,
                    "reference_assets": prompt.reference_assets,
                },
            }
        )

    return scenes


def _boundary_scene(scene: dict | None) -> dict | None:
    if scene is None:
        return None
    return {
        "scene_id": scene["scene_id"],
        "timing": scene["timing"],
        "purpose": scene["purpose"],
        "visual_action": scene["visual_action"],
        "camera": scene["storyboard"]["camera"],
        "composition": scene["storyboard"]["composition"],
        "continuity": scene["storyboard"]["continuity"],
    }


def _chunk_checks(
    checks: list[dict],
    scene_ids: set[str],
) -> list[dict]:
    return [
        item
        for item in checks
        if item.get("scene_id") is None
        or item.get("scene_id") in scene_ids
    ]


def _review_chunk(
    llm: OpenAICompatibleLLM,
    *,
    source: dict,
    episode_facts: list[str],
    scenes: list[dict],
    deterministic_checks: list[dict],
    previous_scene: dict | None,
    next_scene: dict | None,
    chunk_index: int,
) -> FlowPromptReviewOutput:
    scene_ids = {scene["scene_id"] for scene in scenes}
    checks = _chunk_checks(deterministic_checks, scene_ids)

    return run_typed_agent(
        llm,
        FlowPromptReviewOutput,
        system_prompt=SYSTEM_PROMPT,
        payload={
            "source": source,
            "episode_facts": episode_facts,
            "scenes": scenes,
            "boundary_context": {
                "previous": _boundary_scene(previous_scene),
                "next": _boundary_scene(next_scene),
            },
            "deterministic_checks": checks,
        },
        temperature=0.1,
        max_tokens=2600,
        agent_name=f"flow_prompt_review_chunk_{chunk_index}",
    )


def _review_chunk_adaptive(
    llm: OpenAICompatibleLLM,
    *,
    source: dict,
    episode_facts: list[str],
    all_scenes: list[dict],
    scenes: list[dict],
    deterministic_checks: list[dict],
    label: str,
) -> list[FlowPromptReviewOutput]:
    start = all_scenes.index(scenes[0])
    end = start + len(scenes)
    previous_scene = all_scenes[start - 1] if start > 0 else None
    next_scene = all_scenes[end] if end < len(all_scenes) else None

    try:
        review = _review_chunk(
            llm,
            source=source,
            episode_facts=episode_facts,
            scenes=scenes,
            deterministic_checks=deterministic_checks,
            previous_scene=previous_scene,
            next_scene=next_scene,
            chunk_index=label,
        )
        return [review]
    except ValueError as exc:
        message = str(exc)
        if (
            "prompt estimate" not in message
            or "LLM_PROMPT_TOKEN_BUDGET" not in message
            or len(scenes) <= 1
        ):
            raise

        midpoint = (len(scenes) + 1) // 2
        left = scenes[:midpoint]
        right = scenes[midpoint:]

        reviews: list[FlowPromptReviewOutput] = []
        reviews.extend(
            _review_chunk_adaptive(
                llm,
                source=source,
                episode_facts=episode_facts,
                all_scenes=all_scenes,
                scenes=left,
                deterministic_checks=deterministic_checks,
                label=f"{label}a",
            )
        )
        if right:
            reviews.extend(
                _review_chunk_adaptive(
                    llm,
                    source=source,
                    episode_facts=episode_facts,
                    all_scenes=all_scenes,
                    scenes=right,
                    deterministic_checks=deterministic_checks,
                    label=f"{label}b",
                )
            )
        return reviews


def _merge_reviews(
    reviews: list[FlowPromptReviewOutput],
    deterministic_checks: list[dict],
) -> FlowPromptReviewOutput:
    scene_reviews = [
        scene
        for review in reviews
        for scene in review.scene_reviews
    ]
    cross_scene_issues = [
        issue
        for review in reviews
        for issue in review.cross_scene_issues
    ]

    priorities: list[str] = []
    for review in reviews:
        for item in review.revision_priority:
            if item not in priorities:
                priorities.append(item)

    decisions = {review.decision for review in reviews}
    if "BLOCK" in decisions:
        decision = "BLOCK"
    elif "REVISE" in decisions:
        decision = "REVISE"
    else:
        decision = "PASS"

    blocking_checks = [
        item
        for item in deterministic_checks
        if item.get("severity") in {"high", "critical"}
    ]
    if decision == "PASS" and blocking_checks:
        decision = "REVISE"

    score_candidates = [review.overall_score for review in reviews]
    score_candidates.extend(scene.score for scene in scene_reviews)
    overall_score = min(score_candidates) if score_candidates else 0

    summaries = [
        review.executive_summary.strip()
        for review in reviews
        if review.executive_summary.strip()
    ]
    executive_summary = " | ".join(summaries)
    if blocking_checks:
        executive_summary += (
            " | Deterministic preflight found blocking issues; "
            "batch generation remains blocked."
        )

    return FlowPromptReviewOutput(
        overall_score=overall_score,
        decision=decision,
        scene_reviews=scene_reviews,
        cross_scene_issues=cross_scene_issues,
        revision_priority=priorities,
        executive_summary=executive_summary,
    )


def run(
    llm: OpenAICompatibleLLM,
    request: EpisodeRequest,
    script: ScriptOutput,
    storyboard: StoryboardOutput,
    context: ContextOutput,
    veo_prompts: VeoPromptsOutput,
) -> FlowPromptReviewOutput:
    deterministic_checks = run_flow_prompt_checks(
        script=script.model_dump(),
        storyboard=storyboard.model_dump(),
        veo_prompts=veo_prompts.model_dump(),
    )

    compact_scenes = _compact_scene_payload(
        script,
        storyboard,
        veo_prompts,
    )
    if not compact_scenes:
        raise ValueError("No scenes available for Flow prompt review.")

    source = {
        "question": request.question,
        "answer": request.answer,
        "source_notes": request.source_notes,
        "target_duration_s": request.target_duration_s,
    }

    midpoint = (len(compact_scenes) + 1) // 2
    chunks = [
        compact_scenes[:midpoint],
        compact_scenes[midpoint:],
    ]
    chunks = [chunk for chunk in chunks if chunk]

    reviews: list[FlowPromptReviewOutput] = []
    for index, chunk in enumerate(chunks, start=1):
        reviews.extend(
            _review_chunk_adaptive(
                llm,
                source=source,
                episode_facts=context.episode_facts,
                all_scenes=compact_scenes,
                scenes=chunk,
                deterministic_checks=deterministic_checks,
                label=str(index),
            )
        )

    return _merge_reviews(reviews, deterministic_checks)