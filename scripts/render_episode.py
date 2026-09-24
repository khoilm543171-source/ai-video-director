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

    if args.episode_id == "episode_001_fuel_oil_purifier":
        plan_path = PROJECT_ROOT / "outputs" / "episodes" / args.episode_id / "flow_jobs" / "flow_jobs.json"
        if not plan_path.exists():
            parser.error("Build Episode 001 Flow jobs first: python scripts/build_flow_pack.py --episode-id episode_001_fuel_oil_purifier")
        if args.dry_run:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            chosen = [job for job in plan["jobs"] if args.all or job["scene_id"] in args.scene]
            missing = set(args.scene or []) - {job["scene_id"] for job in chosen}
            if missing:
                parser.error("Unknown scene id(s): " + ", ".join(sorted(missing)))
            print(json.dumps({"mode": "flow_manual", "jobs": chosen}, ensure_ascii=False, indent=2))
            return 0
        parser.error("Episode 001 needs in-scene Flow extensions and exact native dialogue. Use flow_jobs/START_HERE.md; this direct Veo API command cannot render the approved 9–13s jobs safely.")

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
