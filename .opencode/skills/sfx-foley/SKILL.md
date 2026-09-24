---
name: sfx-foley
description: Build synchronized MMAudio Foley and ambience prompts from visible scene actions.
---

# SFX / Foley Skill

Use this after a rendered scene exists.

## Prompt structure
Describe only audible events that are visible or strongly implied:
1. base room tone;
2. machinery layer;
3. synchronized foreground Foley;
4. spatial/reverb character.

Example pattern:
"low marine engine-room hum, ventilation airflow, soft pump vibration,
two metallic footsteps on grated steel deck, short valve-wheel creak
synchronized with the hand turn, subtle metal-room resonance"

## Negative prompt
Always exclude:
speech, dialogue, vocals, background music, unrelated alarms,
cinematic impacts, gunshots, crowd noise.

## Rules
- Do not invent alarms, sparks, impacts, leaks, or tool sounds absent from the video.
- Keep ambience continuous and lower than dialogue.
- Foreground Foley should correspond to visible timing.
- Prefer one or two important synchronized events rather than noisy sound soup.
- MMAudio receives the rendered video plus prompt; let visual timing guide the sound.
