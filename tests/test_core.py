from __future__ import annotations

from core.episode_pipeline import EpisodePipeline
from core.llm_client import extract_json_object
from core.schemas import EpisodeRequest, ScriptOutput


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
