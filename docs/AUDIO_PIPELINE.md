# Audio workflow

## Google Flow episodes with native dialogue (Episode 001)

The approved script contains exact dialogue. Render each scene in Flow with
native speech and lip-sync, using the same reference identities and voice
direction across scenes. Keep ship engine-room ambience subtle. **Do not add
music inside Flow.** Keep the eight video scenes separate until they pass
`scripts/check_flow_clips.py` and the human dialogue/lip-sync review in
`docs/EPISODE_001_FLOW.md`.

If a line is missing, repeated or spoken by the wrong character, regenerate
that scene. In particular, listen to the transition between the two in-scene
render steps in scene 07. External voice tools (Chatterbox or Kokoro) are an
optional fallback only when native speech cannot pass review; voice replacement
also requires a renewed visual lip-sync inspection. Never layer external TTS
over already approved native dialogue.

MMAudio is for ambience and visible-action Foley only: exclude speech,
dialogue, vocals and music. ACE-Step is an optional *post-production*
instrumental music source after scene review; it does not add music to Flow
renders. The Episode 001 brief currently requests no music in its eight
deliverable files.

## Other pipeline episodes

The generic `audio_director` stage can create an external `audio_plan.json`
and `audio/mix_audio.py` can combine voice, SFX and music when an episode opts
into external audio production. That generic path does not override the
Episode 001 native Flow policy. In particular, do not run the generic mixer
over Flow files and inadvertently duplicate native dialogue.
