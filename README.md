# AI Video Director — Tiny Engine Cadet

Agentic production pipeline for 60-second vertical Engine Cadet interview videos.

## Current milestone: Episode Pipeline V1

The repository can now turn one question + approved answer into a render-ready episode package:

Question
→ Idea
→ Story
→ Script
→ Storyboard
→ Context Window
→ Veo Scene Prompts
→ Audio Plan
→ ready_for_render

The current milestone intentionally stops before paid video generation so story, timing and continuity can be checked without spending Veo generations.

## Quick start on Windows

1. Pull the latest code.

    git pull

2. Create and activate a Python environment if needed.

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1

3. Install the lightweight orchestrator dependencies.

    pip install -r requirements-orchestrator.txt

4. Create your local environment file.

    Copy-Item .env.example .env

5. Edit .env and set your OpenAI-compatible LLM credentials.

DeepSeek example:

    LLM_BASE_URL=https://api.deepseek.com
    LLM_MODEL=deepseek-chat
    LLM_API_KEY=YOUR_KEY

6. Run the first episode.

    python scripts/run_episode.py --input examples/episode_request.json

A new folder is created automatically under:

    outputs/episodes/ep_.../

Expected files:

    input.json
    idea.json
    story.json
    script.json
    storyboard.json
    context.json
    veo_prompts.json
    audio_plan.json
    manifest.json

A successful planning run ends with:

    "status": "ready_for_render"

## API mode

Start the orchestrator:

    uvicorn api:app --reload --port 8787

Health check:

    http://127.0.0.1:8787/health

Create an episode:

    POST http://127.0.0.1:8787/episodes

Example body:

    {
      "question": "What is the purpose of a fuel oil purifier?",
      "answer": "A fuel oil purifier removes water and solid impurities from fuel oil by centrifugal separation so cleaner fuel can be supplied to the engine.",
      "target_duration_s": 60
    }

This endpoint is what n8n will call later.

## Series consistency

Global series rules live in:

    config/series_bible.json

Recurring character identity lives in:

    config/character_bible.json

Do not duplicate those descriptions inside individual episode data. The Context Builder injects them into the downstream generation context.

## Audio architecture

Audio is split into independent layers so one failure does not require regenerating the whole video.

| Layer | Engine |
|---|---|
| Character voice | Chatterbox |
| Voice fallback | Kokoro-FastAPI |
| Foley / synchronized SFX | MMAudio |
| Background music | ACE-Step 1.5 |
| Mix / duck / loudness | FFmpeg |

The Audio Director generates audio_plan.json during the episode planning stage.

After Veo scenes exist:
- Chatterbox generates dialogue.
- MMAudio watches each finished scene and generates synchronized Foley/SFX.
- ACE-Step generates one continuous instrumental bed for the episode.
- FFmpeg aligns and mixes all layers.
- The future Audio Reviewer can retry only the failed layer.

See docs/AUDIO_PIPELINE.md.

## Audio upstream repositories

| Role | Upstream |
|---|---|
| Character voice | https://github.com/resemble-ai/chatterbox |
| Lightweight fallback | https://github.com/remsky/Kokoro-FastAPI |
| Foley / SFX | https://github.com/hkchengrex/MMAudio |
| Music | https://github.com/ace-step/ACE-Step-1.5 |

Pinned revisions are stored in config/audio_stack.yaml.

To clone the pinned audio repos on Windows:

    .\scripts\bootstrap_audio_repos.ps1

They are placed under vendor/ and intentionally excluded from this repository so their CUDA/PyTorch dependencies remain isolated.

## Validation

Local tests:

    pytest -q

Syntax check:

    python -m compileall core agents services audio scripts api.py

GitHub Actions also runs these checks on push.

## Repository layout

    agents/          planning and directing agents
    audio/           audio mixing logic
    config/          series, characters and audio stack
    contracts/       JSON contracts and examples
    core/            LLM client, schemas, state and episode pipeline
    docs/            implementation notes
    examples/        example episode requests
    prompts/         reusable reviewer/director prompts
    scripts/         CLI and bootstrap scripts
    services/        voice/SFX/music adapters
    tests/           offline smoke tests
    vendor/          external model repos, ignored
    workflows/n8n/   n8n exports
    outputs/         generated episode artifacts, ignored

## Next milestone

Once Episode Pipeline V1 produces a good first package, connect:

Veo render adapter
→ Visual Reviewer
→ scene-level retry
→ Voice / SFX / Music generation
→ FFmpeg final assembly
→ Final multimodal reviewer
→ n8n queue orchestration
