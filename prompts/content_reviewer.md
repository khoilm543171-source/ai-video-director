# Content Reviewer

The Content Reviewer runs after Script and before Storyboard.

It is one LLM call that simulates five independent review lenses:

1. Technical / maritime fidelity
2. Story and retention
3. Interview learning value
4. Production / video-generation feasibility
5. Cross-stage consistency

The supplied EpisodeRequest answer and source_notes are the authoritative
technical source. The reviewer must flag unsupported additions instead of
silently correcting them from outside knowledge.

The structured result contains:
- one 0-100 score per lens,
- overall_score,
- decision: PASS | REVISE | BLOCK,
- strengths,
- issue list with severity/category/scene/evidence,
- concrete repair_instruction,
- revision_priority,
- executive_summary.

Decision policy:
- PASS: overall >= 88, no critical issue, no high-severity technical issue,
  and the final interview answer remains faithful.
- REVISE: the package is repairable.
- BLOCK: the core premise contradicts source material or contains a critical
  unsafe/technical problem.

Pipeline behavior:
- PASS -> continue to Storyboard, Context, Flow/Veo prompts and Audio Plan.
- REVISE/BLOCK -> stop with status needs_content_revision before any video
  generation work.

This mirrors the repository's Audio Reviewer philosophy: review independent
layers, return a structured decision, identify only failed targets, and provide
repair instructions rather than regenerating everything.
