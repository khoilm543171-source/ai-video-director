from __future__ import annotations

import json
from pathlib import Path

from agents import (
    audio_director,
    content_reviewer,
    context_builder,
    flow_prompt_reviewer,
    idea_agent,
    script_agent,
    story_agent,
    storyboard_agent,
    veo_prompt_builder,
)
from core.llm_client import OpenAICompatibleLLM
from core.flow_prompt_checks import run_flow_prompt_checks
from core.provider_router import ProviderRouter
from core.schemas import EpisodeManifest, EpisodeRequest
from core.state_manager import EpisodeStateManager


class EpisodePipeline:
    def __init__(
        self,
        llm: OpenAICompatibleLLM | None = None,
        project_root: str | Path | None = None,
    ):
        self.project_root = (
            Path(project_root).resolve()
            if project_root
            else Path(__file__).resolve().parents[1]
        )
        self.fixed_llm = llm
        self.router = None if llm else ProviderRouter()
        self.state = EpisodeStateManager(
            self.project_root / "outputs" / "episodes"
        )
        self.series_bible = self._load_json(
            self.project_root / "config" / "series_bible.json"
        )
        self.character_bible = self._load_json(
            self.project_root / "config" / "character_bible.json"
        )

    @staticmethod
    def _load_json(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def _llm(self, stage: str):
        if self.fixed_llm is not None:
            return self.fixed_llm
        assert self.router is not None
        return self.router.for_stage(stage)

    def run(self, request: EpisodeRequest) -> EpisodeManifest:
        manifest = self.state.create(request)
        stage = "idea"

        try:
            idea = idea_agent.run(self._llm("idea"), request)
            self.state.save_stage(manifest, "idea", idea.model_dump())

            stage = "story"
            story = story_agent.run(self._llm("story"), request, idea)
            self.state.save_stage(manifest, "story", story.model_dump())

            stage = "script"
            script = script_agent.run(
                self._llm("script"),
                request,
                idea,
                story,
            )
            self._validate_script(script)
            self.state.save_stage(manifest, "script", script.model_dump())

            stage = "content_review"
            review = content_reviewer.run(
                self._llm("content_review"),
                request,
                idea,
                story,
                script,
            )
            self.state.save_stage(
                manifest,
                "content_review",
                review.model_dump(),
                filename="review_report.json",
            )

            if review.decision != "PASS":
                manifest.status = "needs_content_revision"
                manifest.current_stage = "content_review"
                manifest.error = None
                self.state.save_manifest(manifest)
                return manifest

            stage = "storyboard"
            storyboard = storyboard_agent.run(
                self._llm("storyboard"),
                script,
                self.series_bible,
                self.character_bible,
            )
            self._validate_scene_ids(
                [scene.scene_id for scene in script.scenes],
                [scene.scene_id for scene in storyboard.scenes],
                "storyboard",
            )
            self.state.save_stage(
                manifest,
                "storyboard",
                storyboard.model_dump(),
            )

            stage = "context"
            context = context_builder.run(
                request,
                idea,
                script,
                self.series_bible,
                self.character_bible,
            )
            self.state.save_stage(
                manifest,
                "context",
                context.model_dump(),
            )

            stage = "veo_prompts"
            veo_prompts = veo_prompt_builder.run(
                self._llm("veo_prompt_builder"),
                script,
                storyboard,
                context,
            )
            self._validate_scene_ids(
                [scene.scene_id for scene in script.scenes],
                [scene.scene_id for scene in veo_prompts.scenes],
                "veo_prompts",
            )
            self.state.save_stage(
                manifest,
                "veo_prompts",
                veo_prompts.model_dump(),
            )

            stage = "flow_prompt_review"
            issues = run_flow_prompt_checks(
                script=script.model_dump(),
                storyboard=storyboard.model_dump(),
                veo_prompts=veo_prompts.model_dump(),
            )
            blockers = [item for item in issues if item.get("severity") in {"high", "critical"}]
            self.state.save_stage(
                manifest, "flow_prompt_preflight",
                {"render_gate": "BLOCK" if blockers else "PASS", "blocking_issues": blockers,
                 "all_deterministic_issues": issues},
            )
            if blockers:
                manifest.status = "needs_flow_prompt_revision"
                manifest.current_stage = "flow_prompt_preflight"
                manifest.error = None
                self.state.save_manifest(manifest)
                return manifest

            try:
                flow_review = flow_prompt_reviewer.run(
                    self._llm("flow_prompt_review"), request, script, storyboard,
                    context, veo_prompts,
                )
            except Exception as exc:
                self.state.save_stage(
                    manifest, "flow_prompt_review_error",
                    {"advisory_error": f"{type(exc).__name__}: {exc}"},
                )
            else:
                self.state.save_stage(
                    manifest, "flow_prompt_review", flow_review.model_dump(),
                    filename="flow_prompt_review.json",
                )

            stage = "audio_plan"
            audio_plan = audio_director.run(
                self._llm("audio_director"),
                manifest.episode_id,
                script,
                storyboard,
                context,
                self.series_bible,
                self.character_bible,
            )
            self._validate_scene_ids(
                [scene.scene_id for scene in script.scenes],
                [scene.scene_id for scene in audio_plan.scenes],
                "audio_plan",
            )
            self.state.save_stage(
                manifest,
                "audio_plan",
                audio_plan.model_dump(),
            )

            return self.state.mark_complete(manifest)

        except Exception as exc:
            self.state.mark_failed(manifest, stage, exc)
            raise

    @staticmethod
    def _validate_script(script) -> None:
        if not script.scenes:
            raise ValueError("Script has no scenes.")

        previous_end = 0.0
        seen: set[str] = set()

        for scene in script.scenes:
            if scene.scene_id in seen:
                raise ValueError(
                    f"Duplicate script scene id: {scene.scene_id}"
                )
            seen.add(scene.scene_id)

            if scene.end_s <= scene.start_s:
                raise ValueError(
                    f"Invalid scene timing for {scene.scene_id}: "
                    f"{scene.start_s} -> {scene.end_s}"
                )

            if scene.start_s < previous_end - 0.25:
                raise ValueError(
                    f"Overlapping or unordered scene: {scene.scene_id}"
                )

            previous_end = scene.end_s

        if previous_end > script.duration_s + 2:
            raise ValueError(
                "Last scene extends beyond declared script duration."
            )

    @staticmethod
    def _validate_scene_ids(
        expected: list[str],
        actual: list[str],
        stage: str,
    ) -> None:
        if expected != actual:
            raise ValueError(
                f"{stage} scene ids do not match script. "
                f"Expected {expected}, got {actual}"
            )
