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

5. Configure Vilao as the default OpenAI-compatible provider.

    LLM_PROVIDER=vilao
    LLM_FALLBACK_PROVIDER=
    VILAO_BASE_URL=https://api.vilao.ai/v1
    VILAO_API_KEY=YOUR_VILAO_KEY
    VILAO_MODEL=EXACT_MODEL_ID_FROM_VILAO

Do not guess VILAO_MODEL. Copy the exact model ID shown by the Vilao model/provider page or their API example for the route you purchased. A documentation example using gpt-4o only proves the request format; it does not mean your DeepSeek route is named gpt-4o.

6. Check local configuration without exposing your key.

    python scripts/doctor.py

7. Run a very small provider smoke test.

    python scripts/test_llm.py

The smoke test requests a tiny JSON response with max_tokens=64 before you spend tokens on a whole episode.

8. Run project tests only.

    python -m pytest -q tests

pytest.ini prevents pytest from recursively collecting the large upstream test suites under vendor/.

9. Run the first episode.

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

## LLM provider routing

Vilao is the default route because it exposes an OpenAI-compatible chat-completions endpoint. The project only needs a base URL, API key and exact model ID.

Default:

    LLM_PROVIDER=vilao

Optional direct DeepSeek fallback:

    LLM_FALLBACK_PROVIDER=deepseek
    DEEPSEEK_BASE_URL=https://api.deepseek.com
    DEEPSEEK_MODEL=deepseek-chat
    DEEPSEEK_API_KEY=YOUR_DIRECT_DEEPSEEK_KEY

If you do not have a direct DeepSeek API key, leave LLM_FALLBACK_PROVIDER empty.

Individual stages can later use different providers:

    IDEA_LLM_PROVIDER=vilao
    STORY_LLM_PROVIDER=vilao
    SCRIPT_LLM_PROVIDER=vilao
    STORYBOARD_LLM_PROVIDER=vilao
    VEO_PROMPT_BUILDER_LLM_PROVIDER=vilao
    AUDIO_DIRECTOR_LLM_PROVIDER=vilao

This makes it possible to route cheap planning tasks to one provider/model and expensive technical/review tasks to another without rewriting the agents.

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

## Token economy

The orchestrator is designed to avoid sending the full context window to every agent.

Current strategy:
- Context Builder is deterministic and uses no LLM call.
- Each agent receives only the fields it needs.
- JSON payloads and JSON schemas are compacted before sending.
- Schema titles/descriptions/default metadata are stripped from prompts.
- Identical requests are cached locally using SHA-256.
- A per-agent soft input budget stops oversized prompts before they are sent.
- Provider-reported prompt/completion/total token counts are logged when available.
- Output caps are lower per stage to reduce runaway completions.

Default settings in .env:

    LLM_CACHE=true
    LLM_CACHE_DIR=.cache/llm
    LLM_PROMPT_TOKEN_BUDGET=6000
    LLM_USAGE_LOG=outputs/token_usage.jsonl

The cache is local and ignored by Git.

To see which agent consumes the most tokens:

    python scripts/token_report.py

Example report:

    agent                    calls cache     prompt     output      total
    ------------------------------------------------------------------------
    veo_prompt_builder           2     1       2100       1200       3300
    script                       2     1       1500        900       2400
    storyboard                   2     1       1300        850       2150

A cache hit reports zero provider tokens because no API call is made.

The budget is intentionally fail-fast: if one agent grows beyond the configured prompt budget, reduce its context slice instead of increasing the context window by default.

Detailed policy:

    config/token_budget.json