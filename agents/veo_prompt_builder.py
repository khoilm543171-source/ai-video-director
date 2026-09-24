from __future__ import annotations

from core.agent_runtime import run_typed_agent
from core.llm_client import OpenAICompatibleLLM
from core.schemas import ContextOutput, ScriptOutput, StoryboardOutput, VeoPromptsOutput


SYSTEM_PROMPT = """
You are the Video Prompt Compiler for Tiny Engine Cadet.

Turn each storyboard scene into a concise, production-ready visual prompt for a modern text/image-to-video model.

Rules:
- Preserve scene ids and durations exactly.
- Each prompt must contain: recurring visual style, characters present, environment, visible action, camera movement, composition, lighting, and continuity cue.
- Do not generate spoken dialogue or music instructions. Audio is produced by separate agents.
- Do not request subtitles or text baked into the video.
- Reference the fixed character identity instead of redesigning the character.
- Prefer one primary action per scene.
- Keep prompts concrete and visual instead of poetic.
- Negative prompts should combine global negatives with scene-specific failure risks.
- reference_assets may contain stable logical paths such as assets/characters/tiny_cadet.png even if the files are not created yet.
"""


def run(
    llm: OpenAICompatibleLLM,
    script: ScriptOutput,
    storyboard: StoryboardOutput,
    context: ContextOutput,
) -> VeoPromptsOutput:
    return run_typed_agent(
        llm,
        VeoPromptsOutput,
        system_prompt=SYSTEM_PROMPT,
        payload={
            "script": script.model_dump(),
            "storyboard": storyboard.model_dump(),
            "context": context.model_dump(),
            "available_reference_assets": [
                "assets/characters/tiny_cadet.png",
                "assets/characters/chief_engineer.png",
                "assets/environments/engine_room.png",
            ],
        },
        temperature=0.25,
        max_tokens=8000,
    )
