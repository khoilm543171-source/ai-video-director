from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class EpisodeRequest(BaseModel):
    question: str = Field(min_length=3)
    answer: str = Field(min_length=3)
    episode_id: str | None = None
    source_notes: str | None = None
    target_duration_s: int = Field(default=60, ge=30, le=90)


class IdeaOutput(BaseModel):
    title: str
    learning_objective: str
    hook: str
    core_problem: str
    technical_truths: list[str]
    story_premise: str
    payoff: str
    final_interview_answer: str


class StoryBeat(BaseModel):
    beat_id: str
    start_s: float
    end_s: float
    purpose: str
    action: str
    technical_point: str | None = None


class StoryOutput(BaseModel):
    logline: str
    tone: str
    beats: list[StoryBeat]
    continuity_notes: list[str]
    final_interview_answer: str


class DialogueLine(BaseModel):
    character: Literal["tiny_cadet", "chief_engineer", "narrator"]
    text: str
    emotion: str = "neutral"
    delivery: str = "natural"
    start_offset_s: float = 0.0


class ScriptScene(BaseModel):
    scene_id: str
    start_s: float
    end_s: float
    location: str
    purpose: str
    visual_action: str
    dialogue: list[DialogueLine] = Field(default_factory=list)
    on_screen_text: str | None = None
    technical_point: str | None = None


class ScriptOutput(BaseModel):
    title: str
    duration_s: float
    scenes: list[ScriptScene]
    final_interview_question: str
    final_interview_answer: str


class StoryboardScene(BaseModel):
    scene_id: str
    start_s: float
    end_s: float
    shot_type: str
    camera: str
    composition: str
    character_actions: list[str]
    machinery_and_environment: list[str]
    continuity_from_previous: str | None = None
    technical_visualization: str | None = None


class StoryboardOutput(BaseModel):
    aspect_ratio: str = "9:16"
    scenes: list[StoryboardScene]


class ContextOutput(BaseModel):
    series_rules: dict[str, Any]
    characters: dict[str, Any]
    episode_facts: list[str]
    forbidden_visual_errors: list[str]
    global_visual_prompt: str
    negative_prompt: str


class VeoScenePrompt(BaseModel):
    scene_id: str
    duration_s: float
    prompt: str
    negative_prompt: str
    reference_assets: list[str] = Field(default_factory=list)


class VeoPromptsOutput(BaseModel):
    aspect_ratio: str = "9:16"
    scenes: list[VeoScenePrompt]


class EpisodeManifest(BaseModel):
    episode_id: str
    status: str
    question: str
    output_dir: str
    completed_stages: list[str] = Field(default_factory=list)
    current_stage: str | None = None
    files: dict[str, str] = Field(default_factory=dict)
    error: str | None = None
