# Audio Pipeline

The audio system is deliberately split into separate layers so a failed sound does not force a full video rerender.

## Execution order

### 1. Audio Director
Input: approved storyboard + character bible + scene timings.

Output: `audio_plan.json`.

It decides:
- who speaks,
- delivery/emotion,
- scene ambience,
- visible action SFX,
- one episode-level music prompt,
- mix priorities.

### 2. Voice Agent
Primary: Chatterbox.

Recurring characters should use stable reference clips:
- `assets/voices/tiny_cadet.wav`
- `assets/voices/chief_engineer.wav`

Use paralinguistic tags sparingly, e.g. `[chuckle]`.

Fallback: Kokoro-FastAPI for narration or low-resource runs.

### 3. Music Agent
ACE-Step 1.5 generates one continuous 60-second instrumental bed.

Recommended default creative direction:
`playful cinematic miniature adventure, light percussion, subtle industrial texture, warm educational mood, sparse arrangement, no vocals`.

Music can be generated in parallel with video rendering because it does not need the finished frames.

### 4. Foley / SFX Agent
MMAudio runs only after each visual scene is rendered.

Example prompt:
`small engine-room ambience, low diesel machinery hum, ventilation, tiny metallic wrench click synchronized to the visible hand movement, realistic but soft, no speech, no vocals, no background music`.

This is the layer for:
- footsteps,
- valve turns,
- wrench / tool clicks,
- hatch sounds,
- alarms,
- pump / purifier / engine ambience,
- metal impacts,
- room tone.

### 5. Mixer
`audio/mix_audio.py` aligns all clips on the episode timeline.

It:
- delays clips to their scene start time,
- keeps dialogue at the front,
- places Foley below speech,
- keeps music lower,
- side-chain ducks music when dialogue is present,
- targets approximately -14 LUFS / -1 dB true peak.

### 6. Audio Reviewer
The reviewer watches the final video and returns one repair action:
- `RETRY_VOICE`
- `RETRY_SFX`
- `RETRY_MUSIC`
- `REMIX`
- `PASS`

Only the failed layer is regenerated.

## n8n orchestration

Recommended order:

```
Approved Script + Storyboard
        |
        v
Audio Director
   |           \
   |            +--> ACE-Step Music
   v
Voice Agent
   |
   +------------------------+
                            |
Veo Scene Render            |
   |                        |
   v                        |
MMAudio Foley per scene     |
   |                        |
   +-----------+------------+
               v
          FFmpeg Mixer
               |
               v
         Audio Reviewer
          /          \
       FAIL          PASS
        |              |
retry failed layer     v
                  Final MP4
```

Do not ask MMAudio to create the final episode soundtrack. Its job is Foley/ambient synchronization only. Dialogue and music remain separate so they can be controlled and reviewed independently.
