"""OpenAI-compatible API client (also serves local vLLM/SGLang servers).

Thin httpx transport with bounded retries — the audit contract requires
the exact request/response bodies, so no SDK black boxes. Handles the
OpenAI /v1/chat/completions protocol shared by: OpenAI, DeepSeek, xAI,
Mistral, Moonshot, Z.ai, DashScope-compatible endpoints, and every locally
served vLLM/SGLang model (provider ``local_vllm``).
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from ...errors import ProviderError, ProviderRefusal
from ..base import ModelTurn, split_reasoning

RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}
MAX_TRANSPORT_RETRIES = 4


class OpenAICompatTarget:
    """One OpenAI-compatible endpoint, fully audited per call."""

    def __init__(
        self,
        *,
        model_id: str,
        served_id: str,
        base_url: str,
        api_key: str,
        revision: str = "",
        determinism_class: str = "unseeded_api",
        thinking_protocol: str = "none",
        timeout: float = 180.0,
    ) -> None:
        self.model_id = model_id
        self.served_id = served_id
        self.base_url = base_url.rstrip("/")
        self._key = api_key
        self.revision = revision
        self.determinism_class = determinism_class
        self.thinking_protocol = thinking_protocol
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(timeout, connect=15.0),
        )

    # -- transport --------------------------------------------------------------
    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(MAX_TRANSPORT_RETRIES + 1):
            try:
                response = self._client.post("/chat/completions", json=payload)
            except httpx.HTTPError as exc:
                last_error = exc
                time.sleep(min(2**attempt, 8))
                continue
            if response.status_code in RETRYABLE_STATUS:
                last_error = ProviderError(
                    f"status {response.status_code}: {response.text[:200]}",
                    status=response.status_code,
                )
                time.sleep(min(2**attempt, 8))
                continue
            if response.status_code >= 400:
                raise ProviderRefusal(
                    f"HTTP {response.status_code}: {response.text[:300]}",
                    status=response.status_code,
                )
            return response.json()
        raise ProviderError(
            f"transport failed after {MAX_TRANSPORT_RETRIES} retries", last=str(last_error)
        )

    # -- generation ---------------------------------------------------------------
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
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
        }
        if top_k and top_k > 0:
            payload["top_k"] = top_k
        if seed is not None:
            payload["seed"] = seed  # servers: best-effort determinism (recorded class)
        started = time.perf_counter()
        data = self._post(payload)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message", {}) or {}
        raw_output = str(message.get("content") or "")
        reasoning = message.get("reasoning_content") or message.get("reasoning")
        if reasoning:
            turn = ModelTurn(
                raw_output=raw_output,
                content=raw_output,
                reasoning_text=str(reasoning),
                reasoning_parse_status="complete",
                stop_reason=str(choice.get("finish_reason", "unknown")),
            )
        else:
            turn = split_reasoning(raw_output, thinking_mode=self.thinking_protocol == "think_tags")
            turn.stop_reason = str(choice.get("finish_reason", "unknown"))
        usage = data.get("usage", {}) or {}
        turn.token_usage = {
            "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
            "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
        }
        turn.elapsed_ms = elapsed_ms
        turn.model_id = self.model_id
        turn.served_id = self.served_id
        turn.revision = self.revision
        turn.determinism_class = self.determinism_class
        turn.rendered_prompt = ""  # server-side rendering; request body is the record
        turn.input_messages = list(messages)
        turn.generation_params = {k: v for k, v in payload.items() if k != "messages"}
        turn.runtime = {"transport": "openai_compat", "base_url": self.base_url}
        return turn

    def close(self) -> None:
        self._client.close()


__all__ = ["OpenAICompatTarget", "MAX_TRANSPORT_RETRIES"]
