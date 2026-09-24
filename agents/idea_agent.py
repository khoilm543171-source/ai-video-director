from __future__ import annotations

from core.agent_runtime import run_typed_agent
from core.llm_client import OpenAICompatibleLLM
from core.schemas import EpisodeRequest, IdeaOutput


SYSTEM_PROMPT = """
You are the Idea Agent for Tiny Engine Cadet, a 60-second vertical 3D educational series.

Turn one Engine Cadet interview question into a strong micro-story concept.

Rules:
- Technical accuracy is more important than drama.
- Treat the supplied answer as the primary technical truth.
- Do not invent unsafe procedures, fake machinery functions, or fake regulations.
- The story should happen naturally in a merchant-ship engine-room setting.
- Use Tiny Cadet and Chief Engineer as recurring characters.
- Build a problem that makes the interview answer useful.
- Keep the concept visually understandable for a 9:16 short.
- The final interview answer must remain concise and faithful to the supplied answer.
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
            "target_duration_s": request.target_duration_s,
        },
        temperature=0.45,
    )
