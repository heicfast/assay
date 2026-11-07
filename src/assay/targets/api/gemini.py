"""Gemini API client (native generateContent protocol, httpx)."""

from __future__ import annotations

import time
from typing import Any

import httpx

from ...errors import ProviderError, ProviderRefusal
from ..base import ModelTurn

RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}
MAX_TRANSPORT_RETRIES = 4


class GeminiTarget:
    model_id: str
    served_id: str

    def __init__(
        self,
        *,
        model_id: str,
        served_id: str,
        base_url: str,
        api_key: str,
        determinism_class: str = "unseeded_api",
        timeout: float = 180.0,
    ) -> None:
        self.model_id = model_id
        self.served_id = served_id
        self._base = base_url.rstrip("/")
        self._key = api_key
        self._client = httpx.Client(timeout=httpx.Timeout(timeout, connect=15.0))
        self.determinism_class = determinism_class
        self.revision = "api"

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(MAX_TRANSPORT_RETRIES + 1):
            try:
                response = self._client.post(f"{path}?key={self._key}", json=payload)
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
        system_text = "\n".join(m["content"] for m in messages if m.get("role") == "system")
        contents = []
        for m in messages:
            if m.get("role") == "system":
                continue
            role = "model" if m.get("role") == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": m.get("content", "")}]})
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "topP": top_p,
                "maxOutputTokens": max_tokens,
            },
        }
        if top_k and top_k > 0:
            payload["generationConfig"]["topK"] = top_k
        if seed is not None:
            payload["generationConfig"]["seed"] = seed
        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}
        started = time.perf_counter()
        data = self._post(f"/v1beta/models/{self.served_id}:generateContent", payload)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        candidates = data.get("candidates", []) or [{}]
        parts = (candidates[0].get("content", {}) or {}).get("parts", []) or []
        answer_parts = [str(p.get("text", "")) for p in parts if not p.get("thought")]
        thought_parts = [str(p.get("text", "")) for p in parts if p.get("thought")]
        content = "\n".join(p for p in answer_parts if p)
        reasoning = "\n\n".join(p for p in thought_parts if p) or None
        usage = data.get("usageMetadata", {}) or {}
        turn = ModelTurn(
            raw_output=content,
            content=content,
            reasoning_text=reasoning,
            reasoning_parse_status=("complete" if reasoning else "absent"),
            stop_reason=str(candidates[0].get("finishReason", "unknown")),
        )
        turn.token_usage = {
            "prompt_tokens": int(usage.get("promptTokenCount", 0) or 0),
            "completion_tokens": int(usage.get("candidatesTokenCount", 0) or 0),
        }
        turn.elapsed_ms = elapsed_ms
        turn.model_id = self.model_id
        turn.served_id = self.served_id
        turn.revision = self.revision
        turn.determinism_class = self.determinism_class
        turn.input_messages = list(messages)
        turn.generation_params = payload.get("generationConfig", {})
        turn.runtime = {"transport": "gemini"}
        return turn

    def close(self) -> None:
        self._client.close()


__all__ = ["GeminiTarget"]
