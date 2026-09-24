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

Review every scene before Google Flow batch generation.

Rules:
- request.answer, request.source_notes and episode_facts are the technical truth.
- Never silently add outside maritime facts.
- Compare approved script intent/dialogue, storyboard camera/continuity, and final video prompt.
- Dialogue must be exact and realistically fit scene duration.
- The downstream Flow compiler removes legacy audio-suppression phrases and appends exact approved dialogue with native lip-sync.
- Camera instructions must be coherent for vertical 9:16.
- References and continuity must remain stable across scenes.
- Flag overloaded clips with too many simultaneous actions, camera moves, cutaways or dialogue.
- Treat deterministic_checks as mandatory evidence; high/critical findings block PASS.
- PASS only when every scene is batch-safe and no high/critical issue exists.
""" + "\n\n" + compose_skills("flow-prompt-review")


def _compact_scene_payload(
    script: ScriptOutput,
    storyboard: StoryboardOutput,
    veo_prompts: VeoPromptsOutput,
) -> list[dict]:
    board_by_id = {
        scene.scene_id: scene
        for scene in storyboard.scenes
    }
    prompt_by_id = {
        scene.scene_id: scene
        for scene in veo_prompts.scenes
    }

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

    review = run_typed_agent(
        llm,
        FlowPromptReviewOutput,
        system_prompt=SYSTEM_PROMPT,
        payload={
            "source": {
                "question": request.question,
                "answer": request.answer,
                "source_notes": request.source_notes,
                "target_duration_s": request.target_duration_s,
            },
            "episode_facts": context.episode_facts,
            "scenes": compact_scenes,
            "deterministic_checks": deterministic_checks,
        },
        temperature=0.1,
        max_tokens=4200,
        agent_name="flow_prompt_review",
    )

    blocking = any(
        item.get("severity") in {"high", "critical"}
        for item in deterministic_checks
    )
    if review.decision == "PASS" and blocking:
        review.decision = "REVISE"
        review.executive_summary = (
            review.executive_summary
            + " Deterministic preflight found blocking issues; "
            "the batch is not safe to generate yet."
        )

    return review
