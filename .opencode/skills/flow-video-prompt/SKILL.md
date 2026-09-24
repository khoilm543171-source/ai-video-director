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
- No spoken dialogue, music instructions, subtitles, or baked-in text in the video prompt.
- Do not rely on tiny readable gauges or UI text.
- Keep machinery physically plausible for a merchant ship engine room.
- Scene prompt must not contradict the supplied reference image.
