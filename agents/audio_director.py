from __future__ import annotations

from core.agent_runtime import run_typed_agent
from core.llm_client import OpenAICompatibleLLM
from core.schemas import (
    AudioPlanOutput,
    ContextOutput,
    ScriptOutput,
    StoryboardOutput,
)


SYSTEM_PROMPT = """
You are the Audio Director for Tiny Engine Cadet.

Design audio as independent controllable layers: dialogue, Foley/SFX and one continuous music bed.

Rules:
- Preserve every approved dialogue line exactly. Do not rewrite technical wording.
- Use Chatterbox direction for recurring character voices.
- Use paralinguistic tags only when natural and never inside technical terms.
- SFX prompts must describe sounds visible or strongly implied by the rendered scene.
- Every SFX prompt must exclude speech, dialogue, vocals and background music.
- Engine-room ambience should be believable but subtle.
- Generate one continuous instrumental music concept for the full episode, not one song per scene.
- Music should support hook, problem, reveal, explanation and resolution while remaining sparse under technical speech.
- Keep dialogue as the mix priority.
"""


def run(
    llm: OpenAICompatibleLLM,
    episode_id: str,
    script: ScriptOutput,
    storyboard: StoryboardOutput,
    context: ContextOutput,
    series_bible: dict,
    character_bible: dict,
) -> AudioPlanOutput:
    return run_typed_agent(
        llm,
        AudioPlanOutput,
        system_prompt=SYSTEM_PROMPT,
        payload={
            "episode_id": episode_id,
            "duration_s": script.duration_s,
            "script": script.model_dump(),
            "storyboard": storyboard.model_dump(),
            "context": context.model_dump(),
            "series_audio_direction": series_bible.get("audio_direction", {}),
            "character_voice_direction": {
                key: value.get("voice_direction")
                for key, value in character_bible.get("characters", {}).items()
            },
            "reference_voice_paths": {
                "tiny_cadet": "assets/voices/tiny_cadet.wav",
                "chief_engineer": "assets/voices/chief_engineer.wav",
            },
        },
        temperature=0.2,
        max_tokens=8000,
    )
