---
name: visual-review
description: Review rendered Tiny Engine Cadet scene video before audio/post-production.
---

# Visual Review Skill

Use after one scene MP4 has been rendered and before downstream audio/post-production.

## Inputs
- rendered scene video;
- approved script scene;
- approved storyboard scene;
- recurring character and environment rules;
- episode technical facts.

## Review the actual temporal video, not a single still.

Evaluate six independent lenses:

1. character_consistency
- Tiny Cadet and Chief Engineer preserve identity, proportions, helmet, clothing and PPE;
- no face/body drift, duplicate character, random redesign, or wrong uniform.

2. story_match
- visible action matches the approved scene purpose and script;
- required character/object is present;
- no invented event changes the story.

3. maritime_accuracy
- machinery and engine-room context remain plausible;
- no obviously impossible machinery behavior;
- no unsafe behavior is presented as correct;
- do not invent technical claims beyond provided episode facts.

4. camera_quality
- camera follows the approved storyboard intent;
- 9:16 composition keeps the teaching subject readable;
- movement is stable and intentional;
- no accidental jump, wild orbit, whip, severe crop, or disorienting reframing.

5. artifact_quality
- no extra limbs, warped hands, melting machinery, flicker, geometry collapse,
  sudden identity morph, broken object interaction, random text, logo, watermark,
  or severe temporal artifact.

6. continuity
- beginning and end states are usable for adjacent cuts;
- screen direction, character placement, machinery position and lighting are coherent;
- no unexplained teleportation within the scene.

## Decision
PASS only when:
- overall_score >= 88;
- no critical issue;
- no high-severity character, maritime or artifact issue;
- scene meaning still matches approved content.

RETRY_SCENE when a render defect can be fixed by regenerating this scene only.

MANUAL_CHECK when the video is visually ambiguous or the reviewer lacks enough
evidence to make a safe technical/content determination.

## Retry behavior
Never rewrite the whole episode.
Return one concise retry_prompt_delta containing only the changes needed for this scene.

## Output
Return structured JSON only with:
- score for each lens;
- overall_score;
- confidence;
- decision;
- issues with severity/category/time hint/evidence/repair;
- failed_checks;
- retry_prompt_delta;
- summary.
