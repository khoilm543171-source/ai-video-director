"""Compatibility entry point: regenerate Episode 001 from its approved spec.

No regex patches or duration reallocation are performed. Old planning files are
backed up once by the compiler before being atomically replaced.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.flow_prompt_compiler import compile_flow_spec


def main() -> int:
    parser = argparse.ArgumentParser(description="Recompile Episode 001 from the approved Flow spec.")
    parser.add_argument("--episode-id", default="episode_001_fuel_oil_purifier")
    args = parser.parse_args()
    spec = json.loads((PROJECT_ROOT / "examples" / "episode_001_flow.json").read_text(encoding="utf-8"))
    if args.episode_id != spec["episode_id"]:
        parser.error("This compatibility entry point only handles Episode 001.")
    path = compile_flow_spec(spec, PROJECT_ROOT / "outputs" / "episodes")
    print(f"Regenerated eight independent Flow jobs from structured spec: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
