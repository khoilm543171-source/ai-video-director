---
name: voice-direction
description: Direct recurring character voice generation with Chatterbox.
---

# Voice Direction Skill

Use this whenever planning or generating character dialogue.

## Identity
- Tiny Cadet: young adult male, curious, energetic, clear international English, technically credible, never baby-like.
- Chief Engineer: mature male, calm, concise, experienced, mentor-like.

## Generation order
1. preserve approved dialogue text exactly;
2. choose the recurring reference voice;
3. set emotion;
4. set delivery pace and emphasis;
5. add paralinguistic tags only when naturally justified;
6. tune model controls only after identity/text are correct.

## Chatterbox controls
- reference audio is the main identity anchor;
- exaggeration controls expressiveness;
- cfg_weight controls conditioning strength;
- temperature controls variation.

## Rules
- Never paraphrase technical terms during synthesis.
- Never add filler words that alter timing or meaning.
- Use restrained emotion for technical explanation.
- Keep pronunciation of maritime terms intelligible.
- If a line is too long for the scene, flag the script instead of speeding the voice unnaturally.
