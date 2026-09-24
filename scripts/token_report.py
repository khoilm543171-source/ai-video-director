from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize LLM token usage.")
    parser.add_argument(
        "--log",
        type=Path,
        default=Path("outputs/token_usage.jsonl"),
    )
    args = parser.parse_args()

    if not args.log.exists():
        print(f"No usage log found: {args.log}")
        return

    rows = []
    for line in args.log.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))

    if not rows:
        print("Usage log is empty.")
        return

    by_agent = defaultdict(
        lambda: {
            "calls": 0,
            "cache_hits": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_prompt_tokens": 0,
        }
    )

    for row in rows:
        agent = row.get("agent", "unknown")
        bucket = by_agent[agent]
        bucket["calls"] += 1
        bucket["cache_hits"] += int(bool(row.get("cache_hit")))
        bucket["prompt_tokens"] += int(row.get("provider_prompt_tokens") or 0)
        bucket["completion_tokens"] += int(row.get("provider_completion_tokens") or 0)
        bucket["total_tokens"] += int(row.get("provider_total_tokens") or 0)
        bucket["estimated_prompt_tokens"] += int(
            row.get("prompt_estimate_tokens") or 0
        )

    print(
        f"{'agent':24} {'calls':>5} {'cache':>5} "
        f"{'prompt':>10} {'output':>10} {'total':>10}"
    )
    print("-" * 72)

    grand = 0
    for agent, bucket in sorted(
        by_agent.items(),
        key=lambda item: item[1]["total_tokens"],
        reverse=True,
    ):
        grand += bucket["total_tokens"]
        print(
            f"{agent:24} "
            f"{bucket['calls']:>5} "
            f"{bucket['cache_hits']:>5} "
            f"{bucket['prompt_tokens']:>10} "
            f"{bucket['completion_tokens']:>10} "
            f"{bucket['total_tokens']:>10}"
        )

    print("-" * 72)
    print(f"{'TOTAL':24} {'':>5} {'':>5} {'':>10} {'':>10} {grand:>10}")


if __name__ == "__main__":
    main()
