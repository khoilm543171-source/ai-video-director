# AI Video Director — Engine Cadet Tiny 3D

An agentic pipeline for 60-second vertical Engine Cadet interview videos.

## Core flow

Question Bank
→ Story Agent
→ Script Agent
→ Storyboard / Context Builder
→ Veo Render
→ Visual Reviewer
→ Audio Director
→ Voice + Foley/SFX + Music
→ FFmpeg Mix / Ducking / Master
→ Final Review
→ 1080x1920 MP4

## Audio stack

| Role | Upstream | Why |
|---|---|---|
| Character voice | https://github.com/resemble-ai/chatterbox | Voice cloning, expressive speech, paralinguistic tags |
| Lightweight voice fallback | https://github.com/remsky/Kokoro-FastAPI | OpenAI-compatible TTS API, CPU/GPU Docker images |
| Foley / SFX | https://github.com/hkchengrex/MMAudio | Generates synchronized audio from video + text |
| Background music | https://github.com/ace-step/ACE-Step-1.5 | Local music generation, REST API, duration/BPM/style control |
| Mix / master | FFmpeg | Timeline alignment, side-chain ducking, loudness normalization |

## Audio design rule

Voice, SFX and music are generated independently. The Audio Director creates one `audio_plan.json` after the storyboard is approved.

- Voice follows character identity + emotion.
- Foley/SFX is generated after each visual scene exists, so sound can synchronize to movement.
- Background music is generated once per episode for continuity.
- Music is automatically ducked under dialogue.
- Final audio is reviewed separately from the visual review.

## Upstream pins

See `config/audio_stack.yaml` and `scripts/bootstrap_audio_repos.ps1`.

## Repository layout

```
audio/
config/
contracts/
docs/
prompts/
scripts/
services/
vendor/        # ignored; external upstream repos cloned locally
workflows/n8n/
outputs/       # ignored
```

The external model repositories are intentionally not copied into this repository. They run as independent services/environments so CUDA/PyTorch dependency changes do not break the director pipeline.
