---
name: episode-orchestration
description: Run the repetitive Tiny Engine Cadet production workflow with gates and resumable stages.
---

# Episode Orchestration Skill

Use this as the default production SOP.

## Pipeline
Question + approved answer
→ Idea
→ Story
→ Script
→ Content Review
→ human approval gate
→ Storyboard
→ Context
→ Flow/Veo scene prompts
→ reference/ingredient setup
→ scene rendering
→ Visual Review
→ voice
→ SFX/Foley
→ continuous music
→ FFmpeg mix
→ Audio/Final Review
→ final 9:16 MP4.

## Boring-work rules
- Resume from the latest successful stage.
- Never regenerate a successful scene because another scene failed.
- Never spend video credits before content review passes.
- Keep character/environment references stable across the series.
- Store every stage output as structured files.
- Retry only the failed layer: content, scene, voice, SFX, music, or mix.
- Human only needs to approve the creative content gate unless a later reviewer raises a blocking issue.
