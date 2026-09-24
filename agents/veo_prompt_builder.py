from __future__ import annotations

from core.agent_runtime import run_typed_agent
from core.llm_client import OpenAICompatibleLLM
from core.skill_loader import compose_skills
from core.schemas import ContextOutput, ScriptOutput, StoryboardOutput, VeoPromptsOutput


SYSTEM_PROMPT = """
You are the Video Prompt Compiler for Tiny Engine Cadet.

Rules:
- Preserve scene ids and durations exactly.
- Each prompt: fixed style, characters present, environment, visible action,
  camera, composition, lighting and continuity cue.
- Do not invent or paraphrase dialogue; the Flow pack attaches exact approved script dialogue later.
- Do not add music, subtitles or baked-in text.
- Never redesign recurring characters.
- Prefer one primary visible action per scene.
- Keep prompts concrete and visual.
- Do not add "no dialogue audio" or "no lip-sync" instructions; native dialogue may be attached downstream.
- Combine global negatives with scene-specific failure risks.
""" + "\n\n" + compose_skills(
    "flow-video-prompt",
    "camera-direction",
)


def run(
    llm: OpenAICompatibleLLM,
    script: ScriptOutput,
    storyboard: StoryboardOutput,
    context: ContextOutput,
) -> VeoPromptsOutput:
    scene_timing = [
        {
            "scene_id": s.scene_id,
            "start_s": s.start_s,
            "end_s": s.end_s,
        }
        for s in script.scenes
    ]

    compact_context = {
        "global_visual_prompt": context.global_visual_prompt,
        "negative_prompt": context.negative_prompt,
        "characters": context.characters,
        "episode_facts": context.episode_facts,
    }

    return run_typed_agent(
        llm,
        VeoPromptsOutput,
        system_prompt=SYSTEM_PROMPT,
        payload={
            "timing": scene_timing,
            "storyboard": storyboard.model_dump(),
            "context": compact_context,
            "reference_assets": [
                "assets/characters/tiny_cadet.png",
                "assets/characters/chief_engineer.png",
                "assets/environments/engine_room.png",
            ],
        },
        temperature=0.2,
        max_tokens=4500,
        agent_name="veo_prompt_builder",
    )