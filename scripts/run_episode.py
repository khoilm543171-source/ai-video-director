from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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

    manifest = EpisodePipeline(project_root=PROJECT_ROOT).run(request)

    print(
        json.dumps(
            manifest.model_dump(),
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
