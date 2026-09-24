from __future__ import annotations

import json
from pathlib import Path

from core.render_manager import RenderManager
from core.schemas import EpisodeRequest
from core.state_manager import EpisodeStateManager
from renderers.veo_renderer import VeoRenderResult


class FakeRenderer:
    model = "fake-veo"
    aspect_ratio = "9:16"

    @staticmethod
    def _duration(scene):
        return int(round(scene.duration_s))

    def render_scene(self, scene, output_dir, *, overwrite=False):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{scene.scene_id}.mp4"
        path.write_bytes(b"fake-mp4")
        return VeoRenderResult(
            scene_id=scene.scene_id,
            model=self.model,
            output_path=str(path),
            duration_s=self._duration(scene),
            aspect_ratio=self.aspect_ratio,
        )


def make_episode(tmp_path):
    root = tmp_path
    state = EpisodeStateManager(root / "outputs" / "episodes")
    manifest = state.create(
        EpisodeRequest(
            question="What is a purifier?",
            answer="It removes water and solids from fuel.",
            episode_id="test-episode",
        )
    )
    episode_dir = Path(manifest.output_dir)
    prompts = {
        "aspect_ratio": "9:16",
        "scenes": [
            {
                "scene_id": "scene_01",
                "duration_s": 6,
                "prompt": "Tiny Cadet observes a purifier.",
                "negative_prompt": "text, logos",
                "reference_assets": [],
            },
            {
                "scene_id": "scene_02",
                "duration_s": 6,
                "prompt": "Chief points to the purifier bowl.",
                "negative_prompt": "text, logos",
                "reference_assets": [],
            },
        ],
    }
    (episode_dir / "veo_prompts.json").write_text(
        json.dumps(prompts),
        encoding="utf-8",
    )
    return root, manifest


def test_render_manager_dry_run_one_scene(tmp_path):
    root, manifest = make_episode(tmp_path)
    manager = RenderManager(
        project_root=root,
        renderer=FakeRenderer(),
    )

    result = manager.render(
        manifest.episode_id,
        scene_ids=["scene_01"],
        dry_run=True,
    )

    assert result["mode"] == "dry_run"
    assert len(result["scenes"]) == 1
    assert result["scenes"][0]["scene_id"] == "scene_01"


def test_render_manager_renders_and_resumes(tmp_path):
    root, manifest = make_episode(tmp_path)
    renderer = FakeRenderer()
    manager = RenderManager(project_root=root, renderer=renderer)

    first = manager.render(
        manifest.episode_id,
        scene_ids=["scene_01"],
    )
    assert first["scenes"]["scene_01"]["status"] == "rendered"

    episode_dir = Path(manifest.output_dir)
    assert (episode_dir / "scenes" / "scene_01.mp4").exists()

    final = manager.render(manifest.episode_id)
    assert set(final["scenes"]) == {"scene_01", "scene_02"}

    saved = manager.state.load_manifest(manifest.episode_id)
    assert saved.status == "video_scenes_rendered"
    assert "veo_render" in saved.completed_stages
