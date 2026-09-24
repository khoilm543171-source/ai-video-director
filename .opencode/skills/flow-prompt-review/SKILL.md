---
name: flow-prompt-review
description: Audit all Flow/Veo scene prompts before batch generation.
---

# Flow Prompt Review Skill

Use after storyboard/context/video prompts are ready and before Google Flow batch generation.

Review every scene against the approved script, storyboard, context and source technical facts.

## Per-scene checks
1. Technical fidelity
- no invented machinery function, maintenance procedure, alarm, regulation or unsafe instruction;
- visible technical process must stay within supplied episode facts.

2. Dialogue fit
- exact approved words only;
- speaker identity correct;
- dialogue length realistically fits scene duration;
- no instruction elsewhere contradicts native dialogue or lip-sync.

3. References
- every visible/speaking recurring character is explicitly referenced;
- @EngineRoom is used for recurring engine-room scenes;
- no accidental character redesign instructions.

4. Camera
- one dominant camera idea;
- shot size, angle, lens feel, movement and composition are mutually compatible;
- vertical 9:16 teaching subject remains readable.

5. Continuity
- left/right positions, machinery geography, action handoff and lighting make sense from previous scene;
- do not teleport characters or reverse screen direction without motivation.

6. Audio
- native dialogue and ambience instructions do not conflict;
- no background music inside Flow scene generation;
- no scene with dialogue is told to suppress speech/lip-sync.

7. Negative prompt
- must block common visual failures;
- must not block required content.

8. Production feasibility
- one primary visible action;
- avoid overloaded action + camera + cutaway + dialogue combinations that are unrealistic for one short clip.

## Cross-scene checks
- scene durations and narrative order are coherent;
- visual style and character identity stay stable;
- camera variety is intentional rather than random;
- dialogue progression matches the approved script;
- final interview question and answer remain intact.

## Decision
PASS only when every scene is usable for batch generation and there is no high/critical issue.
REVISE when one or more scenes need prompt repair.
BLOCK for a core contradiction or unsafe/unsupported technical premise.

Return concise, actionable repairs. Never rewrite unrelated scenes.
