from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.render_manager import RenderManager


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render Tiny Engine Cadet scenes with Google Veo."
    )
    parser.add_argument("--episode-id", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--scene",
        action="append",
        help="Render one scene id. Repeat to render several scenes.",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Render all scenes. This can incur multiple Veo generations.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print selected prompts without calling Veo.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Regenerate scenes even if the MP4 already exists.",
    )
    args = parser.parse_args()

    manager = RenderManager(project_root=PROJECT_ROOT)

    result = manager.render(
        args.episode_id,
        scene_ids=None if args.all else args.scene,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
