from __future__ import annotations

from core.agent_runtime import run_typed_agent
from core.llm_client import OpenAICompatibleLLM
from core.schemas import EpisodeRequest, IdeaOutput, StoryOutput


SYSTEM_PROMPT = """
You are the Story Builder for Tiny Engine Cadet.

Convert the approved idea into a tight 60-second story arc.

Rules:
- Use approximately 7 to 8 chronological beats.
- Start around second 0 and end at the requested duration.
- Every beat must move either the story or the technical explanation forward.
- Use a clear arc: hook, problem, observation, explanation, realization, interview question, concise answer, resolution.
- Keep continuity simple enough for short AI-generated video scenes.
- Do not introduce new technical claims unless clearly supported by the supplied answer or source notes.
- Avoid dangerous operational behavior. Tiny Cadet learns under supervision.
- The final interview answer must preserve the meaning of the approved answer.
"""


def run(
    llm: OpenAICompatibleLLM,
    request: EpisodeRequest,
    idea: IdeaOutput,
) -> StoryOutput:
    return run_typed_agent(
        llm,
        StoryOutput,
        system_prompt=SYSTEM_PROMPT,
        payload={
            "question": request.question,
            "answer": request.answer,
            "source_notes": request.source_notes,
            "target_duration_s": request.target_duration_s,
            "approved_idea": idea.model_dump(),
        },
        temperature=0.4,
    )
