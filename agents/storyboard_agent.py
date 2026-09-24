from __future__ import annotations

from core.agent_runtime import run_typed_agent
from core.llm_client import OpenAICompatibleLLM
from core.schemas import ScriptOutput, StoryboardOutput
from core.token_economy import (
    minimal_character_visuals,
    minimal_series_visuals,
)


SYSTEM_PROMPT = """
You are the Storyboard Director for Tiny Engine Cadet.
Convert the approved script into precise 9:16 scene plans.

Rules:
- Preserve script scene ids and timing exactly.
- One clear camera idea per scene.
- Keep recurring characters readable in vertical composition.
- Machinery must look plausible for a merchant ship engine room.
- Use a simple cutaway only when needed to explain a technical process.
- Avoid dense labels, readable gauges, logos and complex UI.
- Maintain spatial and character continuity.
"""


def run(
    llm: OpenAICompatibleLLM,
    script: ScriptOutput,
    series_bible: dict,
    character_bible: dict,
) -> StoryboardOutput:
    slim_script = {
        "title": script.title,
        "duration_s": script.duration_s,
        "scenes": [
            {
                "scene_id": s.scene_id,
                "start_s": s.start_s,
                "end_s": s.end_s,
                "location": s.location,
                "purpose": s.purpose,
                "visual_action": s.visual_action,
                "technical_point": s.technical_point,
            }
            for s in script.scenes
        ],
    }

    return run_typed_agent(
        llm,
        StoryboardOutput,
        system_prompt=SYSTEM_PROMPT,
        payload={
            "script": slim_script,
            "series": minimal_series_visuals(series_bible),
            "characters": minimal_character_visuals(character_bible),
        },
        temperature=0.25,
        max_tokens=4000,
        agent_name="storyboard",
    )
