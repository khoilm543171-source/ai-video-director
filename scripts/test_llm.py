from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.provider_router import ProviderRouter


def main() -> int:
    router = ProviderRouter()
    llm = router.for_stage("idea")

    print(f"Route : {llm.model}")
    print(f"URLs  : {llm.base_url}")

    result = llm.chat_json(
        "Return JSON only.",
        'Return exactly this object: {"ok":true,"provider_test":"passed"}',
        temperature=0,
        max_tokens=64,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("Usage:", llm.last_usage)

    if result.get("ok") is True:
        print("LLM route works.")
        return 0

    print("Unexpected response.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
