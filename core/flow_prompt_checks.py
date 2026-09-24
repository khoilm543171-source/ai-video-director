from __future__ import annotations

from typing import Any


def _word_count(text: str) -> int:
    return len([part for part in text.strip().split() if part])


def run_flow_prompt_checks(
    *,
    script: dict[str, Any],
    storyboard: dict[str, Any],
    veo_prompts: dict[str, Any],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    script_scenes = script.get("scenes", [])
    board_scenes = storyboard.get("scenes", [])
    prompt_scenes = veo_prompts.get("scenes", [])

    if not (
        len(script_scenes)
        == len(board_scenes)
        == len(prompt_scenes)
    ):
        issues.append(
            {
                "severity": "critical",
                "scene_id": None,
                "category": "production",
                "finding": (
                    "Scene counts differ between script, storyboard and "
                    "Veo prompts."
                ),
            }
        )
        return issues

    for idx, (s, b, p) in enumerate(
        zip(script_scenes, board_scenes, prompt_scenes),
        start=1,
    ):
        sid = s.get("scene_id") or f"scene_{idx:02d}"

        for label, item in (
            ("storyboard", b),
            ("veo_prompt", p),
        ):
            if item.get("scene_id") != sid:
                issues.append(
                    {
                        "severity": "critical",
                        "scene_id": sid,
                        "category": "continuity",
                        "finding": (
                            f"{label} scene id {item.get('scene_id')} "
                            f"does not match script id {sid}."
                        ),
                    }
                )

        duration = float(p.get("duration_s") or 0)
        script_duration = float(s.get("end_s") or 0) - float(
            s.get("start_s") or 0
        )
        if abs(duration - script_duration) > 0.5:
            issues.append(
                {
                    "severity": "high",
                    "scene_id": sid,
                    "category": "production",
                    "finding": (
                        f"Prompt duration {duration:.1f}s differs from "
                        f"script duration {script_duration:.1f}s."
                    ),
                }
            )

        prompt = str(p.get("prompt") or "")
        negative = str(p.get("negative_prompt") or "")
        if not prompt.strip():
            issues.append(
                {
                    "severity": "critical",
                    "scene_id": sid,
                    "category": "production",
                    "finding": "Video prompt is empty.",
                }
            )

        dialogue = s.get("dialogue", [])
        words = sum(
            _word_count(str(line.get("text") or ""))
            for line in dialogue
        )
        if dialogue and duration > 0:
            words_per_second = words / duration
            if words_per_second > 3.0:
                severity = "high"
            elif words_per_second > 2.6:
                severity = "medium"
            else:
                severity = None

            if severity:
                issues.append(
                    {
                        "severity": severity,
                        "scene_id": sid,
                        "category": "dialogue_timing",
                        "finding": (
                            f"{words} spoken words in {duration:.1f}s "
                            f"({words_per_second:.2f} words/s) may not fit "
                            "natural synchronized dialogue."
                        ),
                    }
                )



        # Dialogue scenes must not contain legacy instructions that
        # suppress the exact native speech/lip-sync added by the Flow compiler.
        if dialogue:
            combined = (prompt + " " + negative).lower()
            audio_conflicts = (
                "no spoken dialogue audio",
                "no dialogue audio",
                "no spoken audio",
                "no lip-sync",
                "lip-sync mouth shapes for spoken words",
            )
            found_conflicts = [
                term for term in audio_conflicts
                if term in combined
            ]
            if found_conflicts:
                issues.append(
                    {
                        "severity": "high",
                        "scene_id": sid,
                        "category": "audio",
                        "finding": (
                            "Dialogue scene contains speech/lip-sync suppression: "
                            + ", ".join(found_conflicts)
                        ),
                    }
                )

        refs = {
            str(item).lower()
            for item in p.get("reference_assets", [])
        }
        speakers = {
            line.get("character")
            for line in dialogue
        }
        if "tiny_cadet" in speakers and not any(
            "tiny_cadet" in ref for ref in refs
        ):
            issues.append(
                {
                    "severity": "high",
                    "scene_id": sid,
                    "category": "character_reference",
                    "finding": "Tiny Cadet speaks but has no reference asset.",
                }
            )
        if "chief_engineer" in speakers and not any(
            "chief_engineer" in ref for ref in refs
        ):
            issues.append(
                {
                    "severity": "high",
                    "scene_id": sid,
                    "category": "character_reference",
                    "finding": (
                        "Chief Engineer speaks but has no reference asset."
                    ),
                }
            )

    return issues