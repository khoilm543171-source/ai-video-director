from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.episode_pipeline import EpisodePipeline
from core.schemas import EpisodeRequest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate one Tiny Engine Cadet episode package."
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to EpisodeRequest JSON.",
    )
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    request = EpisodeRequest.model_validate(payload)

    manifest = EpisodePipeline().run(request)

    print(
        json.dumps(
            manifest.model_dump(),
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
