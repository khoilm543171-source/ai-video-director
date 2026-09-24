from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.schemas import EpisodeManifest, VeoPromptsOutput
from core.state_manager import EpisodeStateManager
from renderers.veo_renderer import VeoRenderer


class RenderManager:
    def __init__(
        self,
        project_root: str | Path | None = None,
        renderer: VeoRenderer | None = None,
    ):
        self.project_root = (
            Path(project_root).resolve()
            if project_root
            else Path(__file__).resolve().parents[1]
        )
        self.state = EpisodeStateManager(
            self.project_root / "outputs" / "episodes"
        )
        self.renderer = renderer or VeoRenderer()

    def load_episode(
        self,
        episode_id: str,
    ) -> tuple[EpisodeManifest, VeoPromptsOutput]:
        manifest = self.state.load_manifest(episode_id)
        prompt_path = Path(manifest.output_dir) / "veo_prompts.json"

        if not prompt_path.exists():
            raise FileNotFoundError(
                f"veo_prompts.json not found for {episode_id}. "
                "Run the planning pipeline first."
            )

        prompts = VeoPromptsOutput.model_validate(
            json.loads(prompt_path.read_text(encoding="utf-8"))
        )
        return manifest, prompts

    def render(
        self,
        episode_id: str,
        *,
        scene_ids: list[str] | None = None,
        overwrite: bool = False,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        manifest, prompts = self.load_episode(episode_id)
        episode_dir = Path(manifest.output_dir)
        scenes_dir = episode_dir / "scenes"
        render_manifest_path = episode_dir / "render_manifest.json"

        selected = prompts.scenes
        if scene_ids:
            wanted = set(scene_ids)
            selected = [
                scene for scene in prompts.scenes
                if scene.scene_id in wanted
            ]
            missing = wanted - {scene.scene_id for scene in selected}
            if missing:
                raise ValueError(
                    "Unknown scene id(s): " + ", ".join(sorted(missing))
                )

        render_manifest = self._load_render_manifest(
            render_manifest_path,
            episode_id,
        )

        if dry_run:
            return {
                "episode_id": episode_id,
                "mode": "dry_run",
                "model": self.renderer.model,
                "aspect_ratio": self.renderer.aspect_ratio,
                "scenes": [
                    {
                        "scene_id": scene.scene_id,
                        "duration_s": self.renderer._duration(scene),
                        "prompt": scene.prompt,
                        "negative_prompt": scene.negative_prompt,
                        "would_write": str(
                            scenes_dir / f"{scene.scene_id}.mp4"
                        ),
                    }
                    for scene in selected
                ],
            }

        manifest.status = "rendering"
        manifest.current_stage = "veo_render"
        self.state.save_manifest(manifest)

        try:
            for scene in selected:
                result = self.renderer.render_scene(
                    scene,
                    scenes_dir,
                    overwrite=overwrite,
                )

                render_manifest["scenes"][scene.scene_id] = {
                    "status": "rendered",
                    "model": result.model,
                    "duration_s": result.duration_s,
                    "aspect_ratio": result.aspect_ratio,
                    "output_path": result.output_path,
                    "updated_at": self._now(),
                }
                self._write_json(
                    render_manifest_path,
                    render_manifest,
                )

            rendered_ids = {
                scene_id
                for scene_id, data in render_manifest["scenes"].items()
                if data.get("status") == "rendered"
            }
            expected_ids = {
                scene.scene_id for scene in prompts.scenes
            }

            if expected_ids.issubset(rendered_ids):
                manifest.status = "video_scenes_rendered"
                manifest.current_stage = None
                if "veo_render" not in manifest.completed_stages:
                    manifest.completed_stages.append("veo_render")
                manifest.files["render_manifest"] = str(
                    render_manifest_path
                )
                manifest.files["scenes_dir"] = str(scenes_dir)
            else:
                manifest.status = "rendering_partial"
                manifest.current_stage = "veo_render"

            self.state.save_manifest(manifest)
            return render_manifest

        except Exception as exc:
            manifest.status = "render_failed"
            manifest.current_stage = "veo_render"
            manifest.error = f"{type(exc).__name__}: {exc}"
            self.state.save_manifest(manifest)
            raise

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _load_render_manifest(
        self,
        path: Path,
        episode_id: str,
    ) -> dict[str, Any]:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))

        return {
            "episode_id": episode_id,
            "renderer": "google-veo",
            "created_at": self._now(),
            "scenes": {},
        }

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
