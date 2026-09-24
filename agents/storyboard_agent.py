from __future__ import annotations

from core.agent_runtime import run_typed_agent
from core.llm_client import OpenAICompatibleLLM
from core.schemas import ScriptOutput, StoryboardOutput


SYSTEM_PROMPT = """
You are the Storyboard Director for Tiny Engine Cadet.

Convert the approved script into visually precise 9:16 scene plans for AI video generation.

Rules:
- Preserve exactly the script scene ids and timing.
- Design one clear camera idea per scene.
- Keep Tiny Cadet and Chief Engineer readable in vertical composition.
- Machinery must look plausible for a merchant ship engine room.
- If a technical process is hard to see physically, describe a simple cutaway or visualized flow without distorting how the system works.
- Avoid dense labels and tiny text because text will be handled later.
- Maintain spatial and character continuity between adjacent scenes.
- Do not ask the video model to invent logos, gauges with readable text, or complex UI.
"""


def run(
    llm: OpenAICompatibleLLM,
    script: ScriptOutput,
    series_bible: dict,
    character_bible: dict,
) -> StoryboardOutput:
    return run_typed_agent(
        llm,
        StoryboardOutput,
        system_prompt=SYSTEM_PROMPT,
        payload={
            "script": script.model_dump(),
            "series_bible": series_bible,
            "character_bible": character_bible,
        },
        temperature=0.3,
        max_tokens=7500,
    )
