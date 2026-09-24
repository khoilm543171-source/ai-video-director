from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from core.schemas import VeoScenePrompt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=False)


class VeoConfigurationError(RuntimeError):
    pass


class VeoRenderError(RuntimeError):
    pass


@dataclass
class VeoRenderResult:
    scene_id: str
    model: str
    output_path: str
    duration_s: int
    aspect_ratio: str


class VeoRenderer:
    """Google GenAI Veo scene renderer.

    Uses the official google-genai SDK. One call renders one scene so a failed
    scene can be retried without regenerating the whole episode.
    """

    def __init__(self):
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise VeoConfigurationError(
                "google-genai is not installed. Run: "
                "pip install -r requirements-orchestrator.txt"
            ) from exc

        self.genai = genai
        self.types = types

        api_key = (
            os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or ""
        ).strip()
        if not api_key:
            raise VeoConfigurationError(
                "Missing GEMINI_API_KEY (or GOOGLE_API_KEY) in .env."
            )

        self.model = os.getenv(
            "VEO_MODEL",
            "veo-3.1-generate-preview",
        ).strip()
        if not self.model:
            raise VeoConfigurationError("VEO_MODEL is empty.")

        self.aspect_ratio = os.getenv("VEO_ASPECT_RATIO", "9:16").strip()
        self.resolution = os.getenv("VEO_RESOLUTION", "").strip()
        self.poll_seconds = max(
            2.0,
            float(os.getenv("VEO_POLL_SECONDS", "10")),
        )
        self.timeout_seconds = max(
            60.0,
            float(os.getenv("VEO_TIMEOUT_SECONDS", "900")),
        )
        self.enhance_prompt = os.getenv(
            "VEO_ENHANCE_PROMPT",
            "true",
        ).lower() not in {"0", "false", "no"}

        forced_duration = os.getenv("VEO_FORCE_DURATION_SECONDS", "").strip()
        self.forced_duration = int(forced_duration) if forced_duration else None

        self.client = genai.Client(api_key=api_key)

    def _duration(self, scene: VeoScenePrompt) -> int:
        if self.forced_duration is not None:
            return self.forced_duration
        return max(1, int(round(scene.duration_s)))

    def render_scene(
        self,
        scene: VeoScenePrompt,
        output_dir: str | Path,
        *,
        overwrite: bool = False,
    ) -> VeoRenderResult:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{scene.scene_id}.mp4"

        if output_path.exists() and not overwrite:
            return VeoRenderResult(
                scene_id=scene.scene_id,
                model=self.model,
                output_path=str(output_path),
                duration_s=self._duration(scene),
                aspect_ratio=self.aspect_ratio,
            )

        duration_s = self._duration(scene)

        config_kwargs = {
            "number_of_videos": 1,
            "duration_seconds": duration_s,
            "aspect_ratio": self.aspect_ratio,
            "negative_prompt": scene.negative_prompt,
            "enhance_prompt": self.enhance_prompt,
        }
        if self.resolution:
            config_kwargs["resolution"] = self.resolution

        source = self.types.GenerateVideosSource(prompt=scene.prompt)

        try:
            operation = self.client.models.generate_videos(
                model=self.model,
                source=source,
                config=self.types.GenerateVideosConfig(**config_kwargs),
            )
        except Exception as exc:
            raise VeoRenderError(
                f"Veo submit failed for {scene.scene_id}: {exc}"
            ) from exc

        started = time.monotonic()

        while not operation.done:
            if time.monotonic() - started > self.timeout_seconds:
                raise VeoRenderError(
                    f"Veo timed out after {self.timeout_seconds:.0f}s "
                    f"for {scene.scene_id}."
                )
            time.sleep(self.poll_seconds)
            try:
                operation = self.client.operations.get(operation)
            except Exception as exc:
                raise VeoRenderError(
                    f"Veo polling failed for {scene.scene_id}: {exc}"
                ) from exc

        response = (
            getattr(operation, "response", None)
            or getattr(operation, "result", None)
        )
        generated = getattr(response, "generated_videos", None)

        if not generated:
            error = getattr(operation, "error", None)
            raise VeoRenderError(
                f"Veo returned no generated video for {scene.scene_id}. "
                f"Operation error: {error}"
            )

        video = generated[0].video

        try:
            self.client.files.download(file=video)
        except Exception as exc:
            raise VeoRenderError(
                f"Veo download failed for {scene.scene_id}: {exc}"
            ) from exc

        video_bytes = getattr(video, "video_bytes", None)
        if not video_bytes:
            raise VeoRenderError(
                f"Downloaded Veo object contains no video_bytes "
                f"for {scene.scene_id}."
            )

        output_path.write_bytes(video_bytes)

        return VeoRenderResult(
            scene_id=scene.scene_id,
            model=self.model,
            output_path=str(output_path),
            duration_s=duration_s,
            aspect_ratio=self.aspect_ratio,
        )
