"""Anthropic Messages API client (native protocol, httpx)."""

from __future__ import annotations

import time
from typing import Any

import httpx

from ...errors import ProviderError, ProviderRefusal
from ..base import ModelTurn

RETRYABLE_STATUS = {408, 429, 500, 502, 503, 529}
MAX_TRANSPORT_RETRIES = 4


class AnthropicTarget:
    model_id: str
    served_id: str

    def __init__(
        self,
        *,
        model_id: str,
        served_id: str,
        base_url: str,
        api_key: str,
        version: str = "2023-06-01",
        determinism_class: str = "unseeded_api",
        timeout: float = 180.0,
    ) -> None:
        self.model_id = model_id
        self.served_id = served_id
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"x-api-key": api_key, "anthropic-version": version},
            timeout=httpx.Timeout(timeout, connect=15.0),
        )
        self.determinism_class = determinism_class
        self.revision = "api"

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(MAX_TRANSPORT_RETRIES + 1):
            try:
                response = self._client.post("/v1/messages", json=payload)
            except httpx.HTTPError as exc:
                last_error = exc
                time.sleep(min(2**attempt, 8))
                continue
            if response.status_code in RETRYABLE_STATUS:
                last_error = ProviderError(f"status {response.status_code}")
                time.sleep(min(2**attempt, 8))
                continue
            if response.status_code >= 400:
                raise ProviderRefusal(f"HTTP {response.status_code}: {response.text[:300]}")
            return response.json()
        raise ProviderError("transport failed", last=str(last_error))

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        top_p: float,
        top_k: int,
        max_tokens: int,
        seed: int | None,
    ) -> ModelTurn:
        payload: dict[str, Any] = {
            "model": self.served_id,
            "messages": [m for m in messages if m.get("role") != "system"] or messages,
            "system": next((m["content"] for m in messages if m.get("role") == "system"), None),
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
        }
        if payload["system"] is None:
            payload.pop("system")
        started = time.perf_counter()
        data = self._post(payload)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        reasoning_parts: list[str] = []
        answer_parts: list[str] = []
        for block in data.get("content", []) or []:
            if block.get("type") == "thinking":
                reasoning_parts.append(str(block.get("thinking", "")))
            else:
                answer_parts.append(str(block.get("text", "")))
        content = "\n".join(p for p in answer_parts if p)
        reasoning = "\n\n".join(p for p in reasoning_parts if p) or None
        usage = data.get("usage", {}) or {}
        turn = ModelTurn(
            raw_output=content,
            content=content,
            reasoning_text=reasoning,
            reasoning_parse_status=("complete" if reasoning else "absent"),
            stop_reason=str(data.get("stop_reason", "unknown")),
        )
        turn.token_usage = {
            "prompt_tokens": int(usage.get("input_tokens", 0) or 0),
            "completion_tokens": int(usage.get("output_tokens", 0) or 0),
        }
        turn.elapsed_ms = elapsed_ms
        turn.model_id = self.model_id
        turn.served_id = self.served_id
        turn.revision = self.revision
        turn.determinism_class = self.determinism_class
        turn.input_messages = list(messages)
        turn.generation_params = {k: v for k, v in payload.items() if k != "messages"}
        turn.runtime = {"transport": "anthropic"}
        return turn

    def close(self) -> None:
        self._client.close()


__all__ = ["AnthropicTarget"]
