from __future__ import annotations

from core.agent_runtime import run_typed_agent
from core.llm_client import OpenAICompatibleLLM
from core.schemas import EpisodeRequest, IdeaOutput, ScriptOutput, StoryOutput


SYSTEM_PROMPT = """
You are the Script Writer for Tiny Engine Cadet.

Write a production-ready script for one 9:16 short.

Rules:
- Prefer 8 scenes, normally 6 to 8 seconds each.
- The full script should fit the requested duration.
- Dialogue must be short enough to speak naturally inside each scene.
- Tiny Cadet sounds curious and technically credible.
- Chief Engineer sounds calm, concise and mentor-like.
- Do not overload every scene with dialogue.
- Show technical ideas visually when possible.
- Do not add technical claims that contradict the supplied answer.
- The last 10 to 15 seconds must clearly contain the interview question and a concise model answer.
- Use only character ids tiny_cadet, chief_engineer, or narrator.
- Do not write camera instructions here; camera planning belongs to storyboard.
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
            "target_duration_s": request.target_duration_s,
            "idea": idea.model_dump(),
            "story": story.model_dump(),
        },
        temperature=0.35,
        max_tokens=7000,
    )
