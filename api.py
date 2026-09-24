from __future__ import annotations

from fastapi import FastAPI, HTTPException

from core.episode_pipeline import EpisodePipeline
from core.schemas import EpisodeManifest, EpisodeRequest
from core.state_manager import EpisodeStateManager


app = FastAPI(
    title="AI Video Director - Tiny Engine Cadet",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "ai-video-director",
        "stage": "episode-pipeline-v1",
    }


@app.post("/episodes", response_model=EpisodeManifest)
def create_episode(request: EpisodeRequest):
    try:
        pipeline = EpisodePipeline()
        return pipeline.run(request)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc


@app.get("/episodes/{episode_id}", response_model=EpisodeManifest)
def get_episode(episode_id: str):
    try:
        state = EpisodeStateManager("outputs/episodes")
        return state.load_manifest(episode_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
