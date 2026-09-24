from __future__ import annotations

from core.agent_runtime import run_typed_agent
from core.llm_client import OpenAICompatibleLLM
from core.skill_loader import compose_skills
from core.schemas import (
    AudioPlanOutput,
    ContextOutput,
    ScriptOutput,
    StoryboardOutput,
)
from core.token_economy import minimal_character_voices


SYSTEM_PROMPT = """
You are the Audio Director for Tiny Engine Cadet.

Rules:
- Keep approved dialogue text exactly unchanged.
- Plan dialogue, Foley/SFX and one continuous music bed separately.
- SFX must match visible or strongly implied actions.
- Every SFX prompt excludes speech, dialogue, vocals and background music.
- Engine-room ambience is believable but subtle.
- Music is instrumental, continuous across the episode and sparse under speech.
- Dialogue is always the mix priority.
""" + "\n\n" + compose_skills(
    "voice-direction",
    "sfx-foley",
    "music-direction",
)


def run(
    llm: OpenAICompatibleLLM,
    episode_id: str,
    script: ScriptOutput,
    storyboard: StoryboardOutput,
    context: ContextOutput,
    series_bible: dict,
    character_bible: dict,
) -> AudioPlanOutput:
    script_audio = {
        "duration_s": script.duration_s,
        "scenes": [
            {
                "scene_id": s.scene_id,
                "start_s": s.start_s,
                "end_s": s.end_s,
                "location": s.location,
                "visual_action": s.visual_action,
                "dialogue": [d.model_dump() for d in s.dialogue],
            }
            for s in script.scenes
        ],
    }

    storyboard_audio = {
        "scenes": [
            {
                "scene_id": s.scene_id,
                "character_actions": s.character_actions,
                "machinery_and_environment": s.machinery_and_environment,
            }
            for s in storyboard.scenes
        ]
    }

    return run_typed_agent(
        llm,
        AudioPlanOutput,
        system_prompt=SYSTEM_PROMPT,
        payload={
            "episode_id": episode_id,
            "script": script_audio,
            "storyboard": storyboard_audio,
            "audio_direction": series_bible.get("audio_direction", {}),
            "voices": minimal_character_voices(character_bible),
            "reference_voice_paths": {
                "tiny_cadet": "assets/voices/tiny_cadet.wav",
                "chief_engineer": "assets/voices/chief_engineer.wav",
            },
        },
        temperature=0.15,
        max_tokens=4500,
        agent_name="audio_director",
    )