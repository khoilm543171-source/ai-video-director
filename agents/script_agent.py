from __future__ import annotations

from core.agent_runtime import run_typed_agent
from core.llm_client import OpenAICompatibleLLM
from core.schemas import EpisodeRequest, IdeaOutput, ScriptOutput, StoryOutput


SYSTEM_PROMPT = """
You are the Script Writer for Tiny Engine Cadet.

Rules:
- Prefer 8 scenes, usually 6 to 8 seconds each.
- Dialogue must fit naturally inside each scene.
- Tiny Cadet: curious and technically credible.
- Chief Engineer: calm, concise, mentor-like.
- Show technical ideas visually; do not overload dialogue.
- Do not contradict supplied technical truths.
- Final 10 to 15 seconds: interview question + concise model answer.
- Character ids: tiny_cadet, chief_engineer, narrator only.
- No camera instructions.
"""


def run(
    llm: OpenAICompatibleLLM,
    request: EpisodeRequest,
    idea: IdeaOutput,
    story: StoryOutput,
) -> ScriptOutput:
    return run_typed_agent(
        llm,
        ScriptOutput,
        system_prompt=SYSTEM_PROMPT,
        payload={
            "question": request.question,
            "answer": request.answer,
            "duration_s": request.target_duration_s,
            "technical_truths": idea.technical_truths,
            "story": story.model_dump(),
        },
        temperature=0.3,
        max_tokens=3500,
        agent_name="script",
    )
