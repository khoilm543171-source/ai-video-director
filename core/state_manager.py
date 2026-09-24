from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.schemas import EpisodeManifest, EpisodeRequest


class EpisodeStateManager:
    def __init__(self, root: str | Path = "outputs/episodes"):
        self.root = Path(root)

    @staticmethod
    def make_episode_id(request: EpisodeRequest) -> str:
        if request.episode_id:
            safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", request.episode_id).strip("-")
            if safe:
                return safe

        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        suffix = uuid.uuid4().hex[:6]
        return f"ep_{stamp}_{suffix}"

    def create(self, request: EpisodeRequest) -> EpisodeManifest:
        episode_id = self.make_episode_id(request)
        episode_dir = self.root / episode_id
        episode_dir.mkdir(parents=True, exist_ok=False)

        self.write_json(episode_dir / "input.json", request.model_dump())

        manifest = EpisodeManifest(
            episode_id=episode_id,
            status="running",
            question=request.question,
            output_dir=str(episode_dir),
            completed_stages=[],
            current_stage="input",
            files={"input": str(episode_dir / "input.json")},
        )
        self.save_manifest(manifest)
        return manifest

    def episode_dir(self, manifest: EpisodeManifest) -> Path:
        return Path(manifest.output_dir)

    def save_stage(
        self,
        manifest: EpisodeManifest,
        stage: str,
        payload: dict[str, Any],
        filename: str | None = None,
    ) -> EpisodeManifest:
        episode_dir = self.episode_dir(manifest)
        path = episode_dir / (filename or f"{stage}.json")
        self.write_json(path, payload)

        if stage not in manifest.completed_stages:
            manifest.completed_stages.append(stage)

        manifest.current_stage = stage
        manifest.files[stage] = str(path)
        self.save_manifest(manifest)
        return manifest

    def mark_complete(self, manifest: EpisodeManifest) -> EpisodeManifest:
        manifest.status = "ready_for_render"
        manifest.current_stage = None
        manifest.error = None
        self.save_manifest(manifest)
        return manifest

    def mark_failed(
        self,
        manifest: EpisodeManifest,
        stage: str,
        error: Exception,
    ) -> EpisodeManifest:
        manifest.status = "failed"
        manifest.current_stage = stage
        manifest.error = f"{type(error).__name__}: {error}"
        self.save_manifest(manifest)
        return manifest

    def save_manifest(self, manifest: EpisodeManifest) -> None:
        path = self.episode_dir(manifest) / "manifest.json"
        self.write_json(path, manifest.model_dump())

    def load_manifest(self, episode_id: str) -> EpisodeManifest:
        path = self.root / episode_id / "manifest.json"
        if not path.exists():
            raise FileNotFoundError(f"Episode not found: {episode_id}")
        return EpisodeManifest.model_validate(
            json.loads(path.read_text(encoding="utf-8"))
        )

    @staticmethod
    def write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
