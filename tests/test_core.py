from __future__ import annotations

from agents.context_builder import run as build_context
from core.episode_pipeline import EpisodePipeline
from core.llm_client import extract_json_object
from core.schemas import EpisodeRequest, IdeaOutput, ScriptOutput
from core.token_economy import compact_json_schema, rough_token_estimate, stable_hash


def test_extract_plain_json():
    assert extract_json_object('{"ok": true}') == {"ok": True}


def test_extract_fenced_json():
    fence = chr(96) * 3
    text = fence + 'json\n{"ok": true, "n": 1}\n' + fence
    assert extract_json_object(text) == {"ok": True, "n": 1}


def test_episode_request_defaults():
    req = EpisodeRequest(
        question="What is a purifier?",
        answer="It separates unwanted contaminants from fuel.",
    )
    assert req.target_duration_s == 60


def test_validate_scene_ids():
    EpisodePipeline._validate_scene_ids(
        ["scene_01", "scene_02"],
        ["scene_01", "scene_02"],
        "test",
    )


def test_validate_script():
    script = ScriptOutput.model_validate(
        {
            "title": "Test",
            "duration_s": 12,
            "final_interview_question": "Q?",
            "final_interview_answer": "A.",
            "scenes": [
                {
                    "scene_id": "scene_01",
                    "start_s": 0,
                    "end_s": 6,
                    "location": "engine room",
                    "purpose": "hook",
                    "visual_action": "Cadet looks at purifier.",
                    "dialogue": [],
                },
                {
                    "scene_id": "scene_02",
                    "start_s": 6,
                    "end_s": 12,
                    "location": "engine room",
                    "purpose": "answer",
                    "visual_action": "Chief points to purifier.",
                    "dialogue": [],
                },
            ],
        }
    )

    EpisodePipeline._validate_script(script)


def test_compact_schema_removes_verbose_metadata():
    schema = {
        "title": "Example",
        "type": "object",
        "properties": {
            "x": {
                "title": "X",
                "description": "Long explanation",
                "type": "string",
            }
        },
    }
    compact = compact_json_schema(schema)
    assert "title" not in compact
    assert "description" not in compact["properties"]["x"]
    assert compact["properties"]["x"]["type"] == "string"


def test_stable_hash_is_deterministic():
    assert stable_hash("a", "b") == stable_hash("a", "b")
    assert stable_hash("a", "b") != stable_hash("a", "c")


def test_token_estimate_increases_with_prompt_size():
    assert rough_token_estimate("a" * 400) > rough_token_estimate("a" * 40)


def test_context_builder_uses_no_llm():
    request = EpisodeRequest(
        question="What is a purifier?",
        answer="A purifier removes water and solids from fuel.",
    )
    idea = IdeaOutput(
        title="Purifier",
        learning_objective="Explain purifier purpose.",
        hook="Dirty fuel arrives.",
        core_problem="Fuel contains contaminants.",
        technical_truths=[
            "A purifier removes water and solid impurities from fuel."
        ],
        story_premise="Cadet investigates dirty fuel.",
        payoff="Cleaner fuel is supplied downstream.",
        final_interview_answer="It removes water and solids from fuel.",
    )
    script = ScriptOutput.model_validate(
        {
            "title": "Purifier",
            "duration_s": 8,
            "final_interview_question": request.question,
            "final_interview_answer": idea.final_interview_answer,
            "scenes": [
                {
                    "scene_id": "scene_01",
                    "start_s": 0,
                    "end_s": 8,
                    "location": "engine room",
                    "purpose": "explain",
                    "visual_action": "Cadet observes the purifier.",
                    "dialogue": [],
                }
            ],
        }
    )
    series = {
        "aspect_ratio": "9:16",
        "visual_style": "tiny 3D",
        "continuity_rules": ["same characters"],
    }
    characters = {
        "characters": {
            "tiny_cadet": {
                "display_name": "Tiny Cadet",
                "role": "Engine Cadet",
                "visual_identity": {"helmet": "white"},
            }
        }
    }

    context = build_context(
        request,
        idea,
        script,
        series,
        characters,
    )

    assert "tiny_cadet" in context.characters
    assert request.answer in context.episode_facts
    assert context.global_visual_prompt


def test_vilao_provider_config(monkeypatch):
    from core.provider_router import ProviderRouter

    monkeypatch.setenv("LLM_PROVIDER", "vilao")
    monkeypatch.setenv("LLM_FALLBACK_PROVIDER", "")
    monkeypatch.setenv("VILAO_API_KEY", "test-key")
    monkeypatch.setenv("VILAO_MODEL", "test-model")
    monkeypatch.setenv("VILAO_BASE_URL", "https://api.vilao.ai/v1")

    routed = ProviderRouter().for_stage("idea")
    assert "vilao:test-model" in routed.model
    assert routed.clients[0].base_url == "https://api.vilao.ai/v1"


def test_stage_provider_override(monkeypatch):
    from core.provider_router import ProviderRouter

    monkeypatch.setenv("LLM_PROVIDER", "vilao")
    monkeypatch.setenv("SCRIPT_LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("LLM_FALLBACK_PROVIDER", "")
    monkeypatch.setenv("VILAO_API_KEY", "vilao-key")
    monkeypatch.setenv("VILAO_MODEL", "vilao-model")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-key")

    routed = ProviderRouter().for_stage("script")
    assert routed.model.startswith("deepseek:")
