from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from core.flow_preflight import check_flow_spec, require_flow_spec
from core.flow_prompt_checks import run_flow_prompt_checks
from core.flow_prompt_compiler import compile_flow_spec
from core.schemas import (ContextOutput, EpisodeRequest, ScriptOutput, StoryboardOutput, VeoPromptsOutput)
from scripts.check_flow_clips import inspect_clips


SPEC = Path(__file__).resolve().parents[1] / "examples" / "episode_001_flow.json"


def approved_spec():
    return json.loads(SPEC.read_text(encoding="utf-8"))


def test_approved_spec_exact_clips_dialogue_and_continuity():
    spec = approved_spec()
    require_flow_spec(spec)
    assert [scene["duration_s"] for scene in spec["scenes"]] == [6, 12, 9, 13, 8, 5, 12, 4]
    assert sum(scene["duration_s"] for scene in spec["scenes"]) == 69
    assert spec["scenes"][6]["dialogue"][0]["text"] == (
        "It removes water and solid impurities from fuel oil by centrifugal separation, "
        "so cleaner fuel is supplied to the engine."
    )


@pytest.mark.parametrize("damage", [
    lambda s: s["scenes"].pop(),
    lambda s: s["scenes"][1].update(state_in="teleported"),
    lambda s: s["scenes"][4].update(chief_side="right"),
    lambda s: s["scenes"][6]["render_steps"]["extend_dialogue"][0].update(text="invented answer"),
    lambda s: s["scenes"][7].update(scene_id="scene_07"),
])
def test_preflight_blocks_structural_production_errors(damage):
    spec = copy.deepcopy(approved_spec())
    damage(spec)
    assert check_flow_spec(spec)
    with pytest.raises(ValueError, match="preflight BLOCK"):
        require_flow_spec(spec)


def test_soft_total_target_does_not_reallocate_or_reject_scene_durations():
    spec = approved_spec()
    spec["target_duration_s"] = 60
    assert not check_flow_spec(spec)
    assert [scene["duration_s"] for scene in spec["scenes"]] == [6, 12, 9, 13, 8, 5, 12, 4]


def test_compiler_writes_eight_independent_jobs_and_consistent_planning(tmp_path):
    spec = approved_spec()
    flow = compile_flow_spec(spec, tmp_path)
    root = flow.parent
    plan = json.loads((flow / "flow_jobs.json").read_text(encoding="utf-8"))
    assert len(plan["jobs"]) == 8
    assert plan["total_duration_s"] == 69
    assert len(list(flow.glob("scene_[0-9][0-9].txt"))) == 8
    assert len([p for p in flow.glob("scene_*_extend.txt")]) == 4
    assert "EXACTLY 8 separate FINAL" in (flow / "FLOW_BATCH_PROMPT.txt").read_text(encoding="utf-8")
    assert "so cleaner fuel is supplied to the engine." in (flow / "scene_07_extend.txt").read_text(encoding="utf-8")
    assert "It removes water and solid impurities" not in (flow / "scene_07_extend.txt").read_text(encoding="utf-8")
    assert "No spoken dialogue audio" not in (flow / "scene_07.txt").read_text(encoding="utf-8")
    metadata = {name: json.loads((root / name).read_text(encoding="utf-8"))
                for name in ("input.json", "script.json", "storyboard.json", "veo_prompts.json", "context.json")}
    assert [s["end_s"] - s["start_s"] for s in metadata["script.json"]["scenes"]] == [6, 12, 9, 13, 8, 5, 12, 4]
    assert [s["duration_s"] for s in metadata["veo_prompts.json"]["scenes"]] == [6, 12, 9, 13, 8, 5, 12, 4]
    assert not run_flow_prompt_checks(script=metadata["script.json"], storyboard=metadata["storyboard.json"], veo_prompts=metadata["veo_prompts.json"])


def test_recompile_preserves_superseded_files_once(tmp_path):
    spec = approved_spec()
    flow = compile_flow_spec(spec, tmp_path)
    script = flow.parent / "script.json"
    script.write_text('{"old":true}', encoding="utf-8")
    (flow.parent / "flow_prompt_review.json").write_text('{"overall_score":60}', encoding="utf-8")
    compile_flow_spec(spec, tmp_path)
    assert (flow / "previous_planning" / "script.json").read_text(encoding="utf-8") == '{"old":true}'
    assert not (flow.parent / "flow_prompt_review.json").exists()
    assert (flow / "previous_planning" / "flow_prompt_review.json").is_file()
    compile_flow_spec(spec, tmp_path)
    assert (flow / "previous_planning" / "script.json").read_text(encoding="utf-8") == '{"old":true}'


def test_native_clip_check_rejects_duration_and_missing_audio(tmp_path, monkeypatch):
    plan = {"jobs": [{"scene_id": "scene_01", "duration_s": 6}]}
    (tmp_path / "scene_01.mp4").write_bytes(b"fake-video")
    def probe(*args, **kwargs):
        return SimpleNamespace(returncode=0, stderr="", stdout=json.dumps({
            "format": {"duration": 8},
            "streams": [{"codec_type": "video", "width": 1080, "height": 1920}],
        }))
    monkeypatch.setattr(subprocess, "run", probe)
    errors = inspect_clips(plan, tmp_path)
    assert any("expected 6s" in item for item in errors)
    assert any("missing native audio" in item for item in errors)


def test_llm_reviewer_submits_one_scene_per_call_without_hard_6000_cap(tmp_path, monkeypatch):
    from agents.flow_prompt_reviewer import run

    flow = compile_flow_spec(approved_spec(), tmp_path)
    root = flow.parent
    monkeypatch.setenv("LLM_CACHE", "false")
    monkeypatch.setenv("LLM_PROMPT_TOKEN_BUDGET", "1")
    monkeypatch.setenv("LLM_PROMPT_BUDGET_MODE", "soft")
    monkeypatch.setenv("LLM_USAGE_LOG", str(tmp_path / "tokens.jsonl"))

    class LocalReviewer:
        model = "fake"
        base_url = "local"
        last_usage = {}

        def __init__(self):
            self.received = []

        def chat_json(self, system, user, **kwargs):
            payload = json.loads(user.split("INPUT:", 1)[1].split("\nOUTPUT_SCHEMA:", 1)[0])
            assert len(payload["scenes"]) == 1
            scene_id = payload["scenes"][0]["scene_id"]
            self.received.append(scene_id)
            return {"overall_score": 80, "decision": "REVISE", "scene_reviews": [
                {"scene_id": scene_id, "score": 80, "decision": "REVISE", "issues": [], "summary": "Advisory"}
            ], "cross_scene_issues": [], "revision_priority": [], "executive_summary": "Advisory only"}

    llm = LocalReviewer()
    load = lambda name: json.loads((root / name).read_text(encoding="utf-8"))
    review = run(
        llm, EpisodeRequest.model_validate(load("input.json")),
        ScriptOutput.model_validate(load("script.json")),
        StoryboardOutput.model_validate(load("storyboard.json")),
        ContextOutput.model_validate(load("context.json")),
        VeoPromptsOutput.model_validate(load("veo_prompts.json")),
    )
    assert llm.received == [f"scene_{i:02d}" for i in range(1, 9)]
    assert review.decision == "REVISE"  # Advice does not change the preflight PASS.
    assert json.loads((root / "flow_prompt_preflight.json").read_text(encoding="utf-8"))["render_gate"] == "PASS"


def test_truncated_provider_reply_is_reported_before_json_parse(monkeypatch):
    from core.llm_client import LLMTransientError, OpenAICompatibleLLM

    class Response:
        status_code = 200
        def json(self):
            return {"choices": [{"message": {"content": '{"cut":'}, "finish_reason": "length"}]}

    monkeypatch.setattr("core.llm_client.requests.post", lambda *a, **k: Response())
    client = OpenAICompatibleLLM(base_url="https://test.invalid", api_key="placeholder", model="test")
    with pytest.raises(LLMTransientError, match="truncated"):
        client.chat_json("system", "user", max_tokens=10)
