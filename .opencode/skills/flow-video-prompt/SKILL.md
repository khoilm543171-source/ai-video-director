---
name: flow-video-prompt
description: Compile storyboard scenes into reusable Google Flow/Veo prompts with reference assets.
---

# Flow / Veo Prompt Skill

Use after script approval and storyboard completion.

## Reference assets
Use recurring references when needed:
- @TinyCadet
- @ChiefEngineer
- @EngineRoom

## Prompt order
1. reference identities to preserve;
2. environment;
3. visible subject/action;
4. blocking;
5. camera grammar from camera-direction skill;
6. lighting;
7. continuity cue;
8. duration and 9:16 instruction;
9. negative prompt.

## Rules
- Describe one primary visible action.
- Never redesign recurring characters.
- Never invent dialogue. Attach the exact approved script dialogue downstream for native synchronized speech when Flow/Veo audio is used.
- No background-music instructions, subtitles, or baked-in text.
- Do not rely on tiny readable gauges or UI text.
- Keep machinery physically plausible for a merchant ship engine room.
- Scene prompt must not contradict the supplied reference image.

## Native dialogue handoff
When building a manual Flow scene prompt:
- append exact approved dialogue after the visual block;
- identify the speaker;
- preserve approved emotion and delivery;
- request natural synchronized lip-sync;
- do not paraphrase or add filler;
- keep ambience subtle and exclude background music.
