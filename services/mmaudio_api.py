from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


app = FastAPI(title="AI Video Director - MMAudio Foley Service", version="0.1.0")


class FoleyRequest(BaseModel):
    video_path: str
    prompt: str = Field(min_length=1)
    negative_prompt: str = "speech, dialogue, vocals, background music"
    duration_s: float = Field(default=8.0, gt=0, le=30)
    variant: str = "large_44k_v2"
    seed: int = 42


@app.get("/health")
def health():
    return {"ok": True, "service": "mmaudio"}


@app.post("/generate")
def generate_foley(req: FoleyRequest):
    project_root = Path(__file__).resolve().parents[1]
    mmaudio_root = Path(
        os.getenv("MMAUDIO_ROOT", project_root / "vendor" / "mmaudio")
    ).resolve()
    python_exe = os.getenv("MMAUDIO_PYTHON", sys.executable)

    video = Path(req.video_path).expanduser().resolve()
    if not video.exists():
        raise HTTPException(status_code=400, detail=f"Video not found: {video}")

    demo = mmaudio_root / "demo.py"
    if not demo.exists():
        raise HTTPException(
            status_code=500,
            detail=f"MMAudio demo.py not found under: {mmaudio_root}",
        )

    output_root = Path(
        os.getenv("AUDIO_OUTPUT_ROOT", project_root / "outputs" / "audio" / "sfx")
    ).resolve()
    run_dir = output_root / f"mmaudio_{uuid.uuid4().hex[:10]}"
    run_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        python_exe,
        str(demo),
        "--variant",
        req.variant,
        "--video",
        str(video),
        "--prompt",
        req.prompt,
        "--negative_prompt",
        req.negative_prompt,
        "--duration",
        str(req.duration_s),
        "--output",
        str(run_dir),
        "--seed",
        str(req.seed),
        "--skip_video_composite",
    ]

    proc = subprocess.run(
        cmd,
        cwd=str(mmaudio_root),
        capture_output=True,
        text=True,
        check=False,
    )

    if proc.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "MMAudio generation failed",
                "stderr": proc.stderr[-4000:],
            },
        )

    expected = run_dir / f"{video.stem}.flac"
    if not expected.exists():
        candidates = list(run_dir.glob("*.flac"))
        if not candidates:
            raise HTTPException(
                status_code=500,
                detail="MMAudio completed but no FLAC output was found",
            )
        expected = candidates[0]

    return {
        "ok": True,
        "path": str(expected),
        "stdout_tail": proc.stdout[-1200:],
    }
