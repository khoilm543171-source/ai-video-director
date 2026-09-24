from __future__ import annotations

from core.agent_runtime import run_typed_agent
from core.llm_client import OpenAICompatibleLLM
from core.flow_prompt_checks import run_flow_prompt_checks
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

You review ALL scene prompts before Google Flow batch generation.

Rules:
- The supplied EpisodeRequest answer/source_notes and Context episode_facts are the technical truth.
- Never silently correct or add outside maritime facts.
- Compare script, storyboard and video prompt scene by scene.
- Dialogue must be exact, fit the scene duration, and never conflict with audio/lip-sync instructions.
- Camera instructions must be internally coherent and suitable for vertical 9:16.
- References and continuity must remain stable across scenes.
- Flag overloaded clips that ask for too many actions, camera moves, cutaways, and dialogue at once.
- PASS only when every scene is batch-safe and no high/critical issue exists.
""" + "\n\n" + compose_skills("flow-prompt-review")


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

    review = run_typed_agent(
        llm,
        FlowPromptReviewOutput,
        system_prompt=SYSTEM_PROMPT,
        payload={
            "source": request.model_dump(),
            "script": script.model_dump(),
            "storyboard": storyboard.model_dump(),
            "context": {
                "episode_facts": context.episode_facts,
                "forbidden_visual_errors": context.forbidden_visual_errors,
                "global_visual_prompt": context.global_visual_prompt,
                "negative_prompt": context.negative_prompt,
            },
            "veo_prompts": veo_prompts.model_dump(),
            "deterministic_checks": deterministic_checks,
        },
        temperature=0.1,
        max_tokens=4200,
        agent_name="flow_prompt_review",
    )