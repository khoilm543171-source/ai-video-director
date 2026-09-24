from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def db(value: float) -> str:
    return f"{value:.2f}dB"


def build_mix_command(manifest: dict[str, Any]) -> list[str]:
    ffmpeg = manifest.get("ffmpeg", "ffmpeg")
    duration_s = float(manifest.get("duration_s", 60))
    output = str(Path(manifest["output"]).expanduser())

    voices = manifest.get("voice", [])
    sfx = manifest.get("sfx", [])
    music = manifest.get("music")

    if not voices and not sfx and not music:
        raise ValueError("Manifest has no audio inputs")

    cmd = [ffmpeg, "-y"]
    inputs: list[dict[str, Any]] = []

    for cue in voices:
        cmd += ["-i", str(Path(cue["path"]).expanduser())]
        inputs.append({"kind": "voice", **cue})

    for cue in sfx:
        cmd += ["-i", str(Path(cue["path"]).expanduser())]
        inputs.append({"kind": "sfx", **cue})

    if music:
        cmd += ["-i", str(Path(music["path"]).expanduser())]
        inputs.append({"kind": "music", **music})

    filters: list[str] = []
    voice_labels: list[str] = []
    sfx_labels: list[str] = []
    music_label: str | None = None

    for i, cue in enumerate(inputs):
        kind = cue["kind"]

        if kind in {"voice", "sfx"}:
            start_ms = int(round(float(cue.get("start_s", 0)) * 1000))
            gain = float(cue.get("gain_db", 0))
            label = f"{kind}{i}"
            filters.append(
                f"[{i}:a]adelay={start_ms}|{start_ms},"
                f"volume={db(gain)},"
                f"atrim=0:{duration_s}[{label}]"
            )
            if kind == "voice":
                voice_labels.append(label)
            else:
                sfx_labels.append(label)

        elif kind == "music":
            gain = float(cue.get("gain_db", -22))
            music_label = f"music{i}"
            filters.append(
                f"[{i}:a]atrim=0:{duration_s},"
                f"volume={db(gain)}[{music_label}]"
            )

    def make_bus(labels: list[str], out_label: str) -> None:
        if not labels:
            return
        if len(labels) == 1:
            filters.append(f"[{labels[0]}]anull[{out_label}]")
        else:
            ins = "".join(f"[{x}]" for x in labels)
            filters.append(
                f"{ins}amix=inputs={len(labels)}:"
                f"normalize=0:dropout_transition=0[{out_label}]"
            )

    make_bus(voice_labels, "voice_bus")
    make_bus(sfx_labels, "sfx_bus")

    final_labels: list[str] = []

    if voice_labels:
        if music_label:
            filters.append("[voice_bus]asplit=2[voice_main][voice_sc]")
            filters.append(
                f"[{music_label}][voice_sc]"
                "sidechaincompress="
                "threshold=0.02:ratio=8:attack=12:release=350"
                "[music_ducked]"
            )
            final_labels += ["voice_main", "music_ducked"]
        else:
            final_labels.append("voice_bus")
    elif music_label:
        final_labels.append(music_label)

    if sfx_labels:
        final_labels.append("sfx_bus")

    if len(final_labels) == 1:
        source = f"[{final_labels[0]}]"
        filters.append(
            source
            + "loudnorm=I=-14:TP=-1.0:LRA=11,"
            + f"atrim=0:{duration_s}[final]"
        )
    else:
        ins = "".join(f"[{x}]" for x in final_labels)
        filters.append(
            f"{ins}amix=inputs={len(final_labels)}:"
            "normalize=0:dropout_transition=0,"
            "loudnorm=I=-14:TP=-1.0:LRA=11,"
            f"atrim=0:{duration_s}[final]"
        )

    Path(output).parent.mkdir(parents=True, exist_ok=True)

    cmd += [
        "-filter_complex",
        ";".join(filters),
        "-map",
        "[final]",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        output,
    ]
    return cmd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    cmd = build_mix_command(manifest)

    print("Running:")
    print(" ".join(cmd))

    result = subprocess.run(cmd, check=False)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
