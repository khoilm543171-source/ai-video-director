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


class AudioVoiceCue(BaseModel):
    character: Literal["tiny_cadet", "chief_engineer", "narrator"]
    text: str
    start_offset_s: float = 0.0
    emotion: str = "neutral"
    delivery: str = "natural"
    paralinguistic_tags: list[str] = Field(default_factory=list)
    reference_voice: str | None = None


class AudioScenePlan(BaseModel):
    scene_id: str
    start_s: float
    duration_s: float
    voice: list[AudioVoiceCue] = Field(default_factory=list)
    sfx_prompt: str
    sfx_negative_prompt: str = "speech, dialogue, vocals, background music"
    ambient_level: float = Field(default=0.45, ge=0, le=1)
    sfx_level: float = Field(default=0.65, ge=0, le=1)


class MusicPlan(BaseModel):
    prompt: str
    duration_s: float
    instrumental: bool = True
    bpm: int | None = None
    mood_arc: list[dict[str, Any]] = Field(default_factory=list)


class AudioPlanOutput(BaseModel):
    episode_id: str
    duration_s: float
    music: MusicPlan
    scenes: list[AudioScenePlan]


class EpisodeManifest(BaseModel):
    episode_id: str
    status: str
    question: str
    output_dir: str
    completed_stages: list[str] = Field(default_factory=list)
    current_stage: str | None = None
    files: dict[str, str] = Field(default_factory=dict)
    error: str | None = None


class ReviewIssue(BaseModel):
    severity: Literal["low", "medium", "high", "critical"]
    category: Literal[
        "technical",
        "story",
        "learning",
        "production",
        "consistency",
    ]
    scene_id: str | None = None
    finding: str
    evidence: str
    repair_instruction: str


class ReviewLensScore(BaseModel):
    score: int = Field(ge=0, le=100)
    reason: str


class ContentReviewOutput(BaseModel):
    technical: ReviewLensScore
    story_retention: ReviewLensScore
    interview_learning: ReviewLensScore
    production_feasibility: ReviewLensScore
    consistency: ReviewLensScore
    overall_score: int = Field(ge=0, le=100)
    decision: Literal["PASS", "REVISE", "BLOCK"]
    strengths: list[str] = Field(default_factory=list)
    issues: list[ReviewIssue] = Field(default_factory=list)
    revision_priority: list[str] = Field(default_factory=list)
    executive_summary: str
