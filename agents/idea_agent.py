from __future__ import annotations

from core.agent_runtime import run_typed_agent
from core.llm_client import OpenAICompatibleLLM
from core.schemas import EpisodeRequest, IdeaOutput


SYSTEM_PROMPT = """
You are the Idea Agent for Tiny Engine Cadet, a 60-second vertical 3D educational series.

Rules:
- Technical accuracy over drama.
- Treat the supplied answer as the primary technical truth.
- No fake machinery functions, unsafe procedures or invented regulations.
- Use Tiny Cadet and Chief Engineer in a merchant-ship engine-room story.
- Build one visually clear problem that makes the answer useful.
- Keep the final interview answer concise and faithful.
"""


def run(llm: OpenAICompatibleLLM, request: EpisodeRequest) -> IdeaOutput:
    return run_typed_agent(
        llm,
        IdeaOutput,
        system_prompt=SYSTEM_PROMPT,
        payload={
            "question": request.question,
            "answer": request.answer,
            "source_notes": request.source_notes,
            "duration_s": request.target_duration_s,
        },
        temperature=0.4,
        max_tokens=1200,
        agent_name="idea",
    )
