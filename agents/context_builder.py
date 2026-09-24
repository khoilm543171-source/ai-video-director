from __future__ import annotations

from core.schemas import ContextOutput, EpisodeRequest, IdeaOutput, ScriptOutput
from core.token_economy import (
    minimal_character_visuals,
    minimal_series_visuals,
)


GLOBAL_NEGATIVE = (
    "character drift, changed face, changed clothing, changed helmet color, "
    "wrong PPE, duplicate people, extra limbs, malformed hands, unreadable "
    "machinery geometry, random logos, baked-in captions, unwanted text, "
    "unrelated rooms, fantasy machinery"
)


def run(
    request: EpisodeRequest,
    idea: IdeaOutput,
    script: ScriptOutput,
    series_bible: dict,
    character_bible: dict,
) -> ContextOutput:
    """Build reusable generation context without spending an LLM call."""

    series_rules = minimal_series_visuals(series_bible)
    characters = minimal_character_visuals(character_bible)

    facts = list(dict.fromkeys(
        [
            request.answer.strip(),
            *[item.strip() for item in idea.technical_truths if item.strip()],
            script.final_interview_answer.strip(),
        ]
    ))

    visual_style = series_rules.get(
        "visual_style",
        "tiny cute stylized 3D animation",
    )

    global_visual_prompt = (
        f"{visual_style}. Merchant ship engine-room setting. "
        "Recurring characters must preserve the exact visual identity supplied "
        "in the character context. Vertical 9:16 composition, clear single "
        "action, cinematic readable lighting, technically plausible machinery."
    )

    forbidden = [
        "change recurring character identity between scenes",
        "change Tiny Cadet white helmet or navy-blue coverall",
        "invent company logos or rank insignia",
        "show unsafe engine-room behavior as correct procedure",
        "distort machinery function for visual drama",
        "bake subtitles or explanatory text into generated video",
    ]

    return ContextOutput(
        series_rules=series_rules,
        characters=characters,
        episode_facts=facts,
        forbidden_visual_errors=forbidden,
        global_visual_prompt=global_visual_prompt,
        negative_prompt=GLOBAL_NEGATIVE,
    )
