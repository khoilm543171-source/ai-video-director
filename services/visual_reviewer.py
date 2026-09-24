from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from core.schemas import VisualReviewOutput
from core.skill_loader import load_skill


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=False)


class VisualReviewConfigurationError(RuntimeError):
    pass


class VisualReviewError(RuntimeError):
    pass


class GeminiVisualReviewer:
    """Review one short rendered scene using Gemini multimodal video input."""

    def __init__(self):
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise VisualReviewConfigurationError(
                "google-genai is not installed. Run: "
                "pip install -r requirements-orchestrator.txt"
            ) from exc

        key = (
            os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or ""
        ).strip()
        if not key:
            raise VisualReviewConfigurationError(
                "Missing GEMINI_API_KEY (or GOOGLE_API_KEY) in .env."
            )

        self.model = os.getenv(
            "VISUAL_REVIEW_MODEL",
            "gemini-2.5-flash",
        ).strip()
        if not self.model:
            raise VisualReviewConfigurationError(
                "VISUAL_REVIEW_MODEL is empty."
            )

        self.max_mb = max(
            1.0,
            float(os.getenv("VISUAL_REVIEW_MAX_MB", "20")),
        )
        self.genai = genai
        self.types = types
        self.client = genai.Client(api_key=key)
        self.system_instruction = load_skill("visual-review")

    def review_scene(
        self,
        *,
        scene_id: str,
        video_path: str | Path,
        script_scene: dict[str, Any],
        storyboard_scene: dict[str, Any],
        episode_facts: list[str],
        character_rules: dict[str, Any],
        environment_rules: dict[str, Any],
    ) -> VisualReviewOutput:
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Scene video not found: {video_path}")

        size_mb = video_path.stat().st_size / (1024 * 1024)
        if size_mb > self.max_mb:
            raise VisualReviewError(
                f"Scene video is {size_mb:.1f} MB, above "
                f"VISUAL_REVIEW_MAX_MB={self.max_mb:.1f}. "
                "Use a smaller review proxy or raise the limit deliberately."
            )

        payload = {
            "scene_id": scene_id,
            "script_scene": script_scene,
            "storyboard_scene": storyboard_scene,
            "episode_facts": episode_facts,
            "character_rules": character_rules,
            "environment_rules": environment_rules,
            "instruction": (
                "Review the attached full scene video temporally. "
                "Do not review hypothetical content. Base visual findings on "
                "what is actually visible in the MP4."
            ),
        }

        prompt = (
            "REVIEW_INPUT:\n"
            + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    self.types.Part.from_text(text=prompt),
                    self.types.Part.from_bytes(
                        data=video_path.read_bytes(),
                        mime_type="video/mp4",
                    ),
                ],
                config=self.types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.1,
                    response_mime_type="application/json",
                    response_schema=VisualReviewOutput,
                ),
            )
        except Exception as exc:
            raise VisualReviewError(
                f"Visual review request failed for {scene_id}: {exc}"
            ) from exc

        if not response.text:
            raise VisualReviewError(
                f"Visual reviewer returned an empty response for {scene_id}."
            )

        try:
            review = VisualReviewOutput.model_validate_json(response.text)
        except Exception as exc:
            raise VisualReviewError(
                f"Visual reviewer returned invalid JSON for {scene_id}: {exc}"
            ) from exc

        # Deterministic safety gate: the model may not PASS below our threshold.
        critical = any(
            issue.severity == "critical"
            for issue in review.issues
        )
        high_blocking = any(
            issue.severity == "high"
            and issue.category
            in {
                "character_consistency",
                "maritime_accuracy",
                "artifact_quality",
            }
            for issue in review.issues
        )

        if (
            review.decision == "PASS"
            and (
                review.overall_score < 88
                or critical
                or high_blocking
            )
        ):
            review.decision = "RETRY_SCENE"

        return review
