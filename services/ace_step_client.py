from __future__ import annotations

import json
import os
import time
from typing import Any

import requests


class AceStepClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or os.getenv("ACESTEP_URL", "http://127.0.0.1:8001")).rstrip("/")
        self.api_key = api_key or os.getenv("ACESTEP_API_KEY")

    @property
    def headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def submit(
        self,
        prompt: str,
        duration_s: float = 60.0,
        bpm: int | None = None,
        model: str = "acestep-v15-turbo",
        thinking: bool = False,
        batch_size: int = 1,
    ) -> str:
        payload: dict[str, Any] = {
            "prompt": prompt,
            "lyrics": "",
            "audio_duration": duration_s,
            "model": model,
            "thinking": thinking,
            "batch_size": batch_size,
            "audio_format": "wav",
        }
        if bpm is not None:
            payload["bpm"] = bpm

        response = requests.post(
            f"{self.base_url}/release_task",
            headers=self.headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        body = response.json()

        if body.get("code") != 200:
            raise RuntimeError(body.get("error") or f"ACE-Step submit failed: {body}")

        return body["data"]["task_id"]

    def query(self, task_id: str) -> dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/query_result",
            headers=self.headers,
            json={"task_id_list": [task_id]},
            timeout=60,
        )
        response.raise_for_status()
        body = response.json()

        if body.get("code") != 200:
            raise RuntimeError(body.get("error") or f"ACE-Step query failed: {body}")

        rows = body.get("data") or []
        if not rows:
            raise RuntimeError(f"No ACE-Step result for task {task_id}")
        return rows[0]

    def wait(self, task_id: str, poll_s: float = 3.0, timeout_s: float = 900.0) -> list[dict[str, Any]]:
        deadline = time.time() + timeout_s

        while time.time() < deadline:
            row = self.query(task_id)
            status = int(row.get("status", 0))

            if status == 1:
                result = row.get("result") or "[]"
                return json.loads(result) if isinstance(result, str) else result

            if status == 2:
                raise RuntimeError(f"ACE-Step task failed: {row}")

            time.sleep(poll_s)

        raise TimeoutError(f"ACE-Step task timed out: {task_id}")
