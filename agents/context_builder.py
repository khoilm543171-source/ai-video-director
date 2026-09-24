from __future__ import annotations

from core.agent_runtime import run_typed_agent
from core.llm_client import OpenAICompatibleLLM
from core.schemas import ContextOutput, EpisodeRequest, IdeaOutput, ScriptOutput


SYSTEM_PROMPT = """
You are the Context Builder for a recurring AI-generated 3D series.

Your job is to compile a compact context window that downstream video prompts can reuse.

Rules:
- Preserve character identity from the character bible exactly.
- Preserve the global visual style from the series bible.
- Extract episode facts only from the supplied question, answer, source notes, approved idea, and approved script.
- Put visual continuity risks into forbidden_visual_errors.
- Build one global_visual_prompt that can prefix every scene prompt.
- Build one strong negative_prompt that rejects character drift, wrong PPE, duplicate people, extra limbs, unreadable machine geometry, random logos, unwanted text overlays, and unrelated environments.
- Do not rewrite the story. This object exists only to stabilize generation.
"""


def run(
    llm: OpenAICompatibleLLM,
    request: EpisodeRequest,
    idea: IdeaOutput,
    script: ScriptOutput,
    series_bible: dict,
    character_bible: dict,
) -> ContextOutput:
    return run_typed_agent(
        llm,
        ContextOutput,
        system_prompt=SYSTEM_PROMPT,
        payload={
            "question": request.question,
            "answer": request.answer,
            "source_notes": request.source_notes,
            "approved_idea": idea.model_dump(),
            "approved_script": script.model_dump(),
            "series_bible": series_bible,
            "character_bible": character_bible,
        },
        temperature=0.2,
    )
