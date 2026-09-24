from __future__ import annotations

from core.agent_runtime import run_typed_agent
from core.llm_client import OpenAICompatibleLLM
from core.schemas import EpisodeRequest, IdeaOutput, StoryOutput


SYSTEM_PROMPT = """
You are the Story Builder for Tiny Engine Cadet.

Rules:
- Build 7 to 8 chronological beats across the requested duration.
- Arc: hook, problem, observation, explanation, realization, interview question,
  concise answer, resolution.
- Every beat moves story or technical learning forward.
- Keep continuity simple for short AI-generated scenes.
- Do not introduce technical claims beyond supplied facts.
- Tiny Cadet learns under supervision; avoid unsafe behavior.
"""


def run(
    llm: OpenAICompatibleLLM,
    request: EpisodeRequest,
    idea: IdeaOutput,
) -> StoryOutput:
    idea_summary = {
        "title": idea.title,
        "hook": idea.hook,
        "core_problem": idea.core_problem,
        "technical_truths": idea.technical_truths,
        "story_premise": idea.story_premise,
        "payoff": idea.payoff,
        "final_interview_answer": idea.final_interview_answer,
    }

    return run_typed_agent(
        llm,
        StoryOutput,
        system_prompt=SYSTEM_PROMPT,
        payload={
            "question": request.question,
            "answer": request.answer,
            "source_notes": request.source_notes,
            "duration_s": request.target_duration_s,
            "idea": idea_summary,
        },
        temperature=0.35,
        max_tokens=2200,
        agent_name="story",
    )
