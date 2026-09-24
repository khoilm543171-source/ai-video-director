---
name: content-review
description: Review idea, story, and script before any expensive rendering.
---

# Content Review Skill

Review the original question/answer plus idea, story, and script through five lenses:
1. technical/maritime fidelity;
2. story/retention;
3. interview-learning value;
4. production feasibility;
5. cross-stage consistency.

## Source rule
The supplied answer and source_notes are authoritative.
Flag unsupported technical additions instead of silently correcting them.

## Decision
- PASS: overall >= 88, no critical issue, no high technical issue, final answer faithful.
- REVISE: repairable story, timing, clarity, or unsupported-claim issues.
- BLOCK: critical contradiction, unsafe instruction, or unusable core premise.

Every issue must include severity, category, evidence, and one concrete repair instruction.
Do not regenerate unrelated parts.
