from __future__ import annotations

import os
import uuid
from pathlib import Path

import torch
import torchaudio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from chatterbox.tts_turbo import ChatterboxTurboTTS


app = FastAPI(title="AI Video Director - Chatterbox Voice Service", version="0.1.0")

_MODEL = None


def get_model():
    global _MODEL
    if _MODEL is None:
        device = os.getenv("CHATTERBOX_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
        use_nano = os.getenv("CHATTERBOX_NANO", "false").lower() == "true"
        _MODEL = ChatterboxTurboTTS.from_pretrained(device=device, nano=use_nano)
    return _MODEL


class VoiceRequest(BaseModel):
    text: str = Field(min_length=1)
    reference_audio: str | None = None
    output_name: str | None = None


@app.get("/health")
def health():
    return {"ok": True, "service": "chatterbox"}


@app.post("/synthesize")
def synthesize(req: VoiceRequest):
    model = get_model()

    output_root = Path(
        os.getenv("AUDIO_OUTPUT_ROOT", "outputs/audio/voice")
    ).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    if req.reference_audio:
        ref = Path(req.reference_audio).expanduser().resolve()
        if not ref.exists():
            raise HTTPException(status_code=400, detail=f"Reference voice not found: {ref}")
        wav = model.generate(req.text, audio_prompt_path=str(ref))
    else:
        wav = model.generate(req.text)

    filename = req.output_name or f"voice_{uuid.uuid4().hex[:12]}.wav"
    if not filename.lower().endswith(".wav"):
        filename += ".wav"

    out = output_root / filename
    torchaudio.save(str(out), wav, model.sr)

    return {
        "ok": True,
        "path": str(out),
        "sample_rate": int(model.sr),
    }
