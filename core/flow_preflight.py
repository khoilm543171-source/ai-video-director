"""Offline hard gate for a structured Google Flow episode specification."""

from __future__ import annotations

import re
from typing import Any


def check_flow_spec(spec: dict[str, Any]) -> list[dict[str, str | None]]:
    issues: list[dict[str, str | None]] = []

    def issue(scene_id: str | None, finding: str) -> None:
        issues.append({"severity": "high", "scene_id": scene_id,
                       "category": "preflight", "finding": finding})

    scenes = spec.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        issue(None, "No scene jobs are defined.")
        return issues
    if len(scenes) != spec.get("expected_clips"):
        issue(None, "Scene count differs from expected_clips.")
    if spec.get("expected_clips") == 8 and len(scenes) != 8:
        issue(None, "Episode 001 requires exactly eight separate scenes.")

    for field in ("style", "environment", "tiny_cadet", "chief_engineer", "purifier", "geography", "audio", "avoid"):
        if not str(spec.get("global", {}).get(field) or "").strip():
            issue(None, f"Missing shared reference/rule: {field}.")
    if not str(spec.get("technical_truth") or "").strip():
        issue(None, "Approved technical truth is missing.")
    question_scene = next((s for s in scenes if isinstance(s, dict) and s.get("scene_id") == "scene_06"), None)
    if spec.get("interview_question") and question_scene and isinstance(question_scene.get("dialogue"), list) and [line.get("text") for line in question_scene["dialogue"] if isinstance(line, dict)] != [spec["interview_question"]]:
        issue("scene_06", "Interview question differs from the approved question.")

    total = 0.0
    seen: set[str] = set()
    previous: dict[str, Any] | None = None
    for index, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict):
            issue(None, f"Scene {index} must be an object.")
            continue
        sid = str(scene.get("scene_id") or "")
        if sid != f"scene_{index:02d}" or sid in seen:
            issue(sid or None, f"Scene order/ID invalid: expected scene_{index:02d}.")
        seen.add(sid)
        duration = scene.get("duration_s")
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration <= 0:
            issue(sid, "Duration must be a positive number of seconds.")
        else:
            total += duration

        for field in ("state_in", "state_out", "camera", "action", "composition", "audio_timing", "end_pose"):
            if not str(scene.get(field) or "").strip():
                issue(sid, f"Missing {field}.")
        if previous and previous.get("state_out") != scene.get("state_in"):
            issue(sid, f"State handoff differs from {previous.get('scene_id')} end pose.")
        previous = scene

        for field, value in (("chief_side", "left"), ("cadet_side", "right"),
                             ("fuel_direction", "left_to_right"),
                             ("purifier_orientation", "inlet_left_outlet_right")):
            if scene.get(field) != value:
                issue(sid, f"Continuity lock {field} must be {value}.")

        lines = scene.get("dialogue")
        if not isinstance(lines, list):
            issue(sid, "dialogue must be a list of approved lines.")
        else:
            for line in lines:
                if not isinstance(line, dict) or line.get("character") not in {"tiny_cadet", "chief_engineer"} or not str(line.get("text") or "").strip():
                    issue(sid, "Dialogue must identify an approved character and exact nonempty words.")

        if isinstance(duration, (int, float)) and duration > 8:
            steps = scene.get("render_steps")
            if not isinstance(steps, dict) or not isinstance(steps.get("base_dialogue"), list) or not isinstance(steps.get("extend_dialogue"), list):
                issue(sid, "A scene longer than the native 8s generation requires base/extend dialogue steps.")
            elif isinstance(lines, list):
                if not all(str(steps.get(f"{phase}_action") or "").strip() for phase in ("base", "extend")):
                    issue(sid, "Long scenes require phase-specific base/extend actions.")
                merged: list[dict[str, str]] = []
                for fragment in steps["base_dialogue"] + steps["extend_dialogue"]:
                    if not isinstance(fragment, dict) or not fragment.get("text"):
                        issue(sid, "Invalid dialogue fragment in render_steps.")
                        break
                    if merged and merged[-1]["character"] == fragment.get("character"):
                        merged[-1]["text"] += " " + fragment["text"]
                    else:
                        merged.append({"character": fragment.get("character"), "text": fragment["text"]})
                if merged != lines:
                    issue(sid, "Base + extension dialogue does not reconstruct exact approved dialogue.")

        positive = " ".join(str(scene.get(key) or "") for key in ("camera", "action", "composition", "audio_timing"))
        positive += " " + " ".join(str(line.get("text") or "") for line in (lines or []) if isinstance(line, dict))
        for term in spec.get("forbidden_claim_terms", []):
            if re.search(r"\b" + re.escape(term) + r"\b", positive, re.I):
                issue(sid, f"Unapproved technical detail in scene: {term}.")
        if re.search(r"\b(?:Chief Engineer|Chief)\s+(?:is\s+)?(?:on\s+)?(?:screen[- ]?)?right\b|\b(?:Tiny Cadet|Cadet)\s+(?:is\s+)?(?:on\s+)?(?:screen[- ]?)?left\b", positive, re.I):
            issue(sid, "Written shot reverses locked Chief/Cadet screen sides.")
        if re.search(r"(?:no spoken dialogue audio|no dialogue audio|no lip-sync|no spoken audio)", positive, re.I):
            issue(sid, "Written scene suppresses native dialogue/lip-sync.")

    # target_duration_s is advisory. The sum of the locked scene durations wins.
    return issues


def require_flow_spec(spec: dict[str, Any]) -> None:
    issues = check_flow_spec(spec)
    if issues:
        raise ValueError("Flow preflight BLOCK:\n" + "\n".join(
            f"{item['scene_id'] or 'episode'}: {item['finding']}" for item in issues
        ))
