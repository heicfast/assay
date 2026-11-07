"""Fail-closed cost ledger (NDJSON, append-only).

When cumulative metered spend crosses the hard cap the ledger REFUSES
further metering — which surfaces as a provider error and stops the run,
never silently exceeding the grant. Compute hours are metered alongside
API spend so one ``costs/summary.json`` answers "what did this study cost".
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..errors import BudgetExceededError


class CostLedger:
    def __init__(
        self, directory: str | Path, *, hard_cap_usd: float, warn_at_fraction: float = 0.8
    ) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.events_path = self.directory / "cost_events.jsonl"
        self.hard_cap_usd = hard_cap_usd
        self.warn_fraction = warn_at_fraction
        self._total_usd = 0.0
        self._api_usd = 0.0
        self._compute_hours = 0.0
        self._calls = 0
        self._warned = False
        # replay existing events so resume does not reset the meter
        if self.events_path.exists():
            for line in self.events_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                event = json.loads(line)
                if event.get("kind") == "api_call" and event.get("cost_usd") is not None:
                    self._total_usd += float(event["cost_usd"])
                    self._api_usd += float(event["cost_usd"])
                    self._calls += 1
                elif event.get("kind") == "compute_hours":
                    self._total_usd += float(event.get("cost_usd", 0.0))
                    self._compute_hours += float(event.get("hours", 0.0))

    def record(
        self,
        *,
        provider: str,
        model_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        price_per_mtok: tuple[float, float],
    ) -> dict[str, Any]:
        prompt_price, completion_price = price_per_mtok
        cost_usd = prompt_tokens * prompt_price / 1e6 + completion_tokens * completion_price / 1e6
        event = {
            "schema_version": "1.0.0",
            "recorded_at_utc": datetime.now(UTC).isoformat(),
            "kind": "api_call",
            "provider": provider,
            "model_id": model_id,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "price_usd_per_mtok": {"prompt": prompt_price, "completion": completion_price},
            "cost_usd": round(cost_usd, 6),
        }
        self._total_usd += cost_usd
        self._api_usd += cost_usd
        self._calls += 1
        self._append(event)
        self._check_cap()
        self._check_warn()
        return event

    def record_compute(
        self, *, instance_type: str, hours: float, usd_per_hour: float, source_url: str = ""
    ) -> dict[str, Any]:
        cost_usd = hours * usd_per_hour
        event = {
            "schema_version": "1.0.0",
            "recorded_at_utc": datetime.now(UTC).isoformat(),
            "kind": "compute_hours",
            "instance_type": instance_type,
            "hours": hours,
            "usd_per_hour": usd_per_hour,
            "cost_usd": round(cost_usd, 4),
            "source_url": source_url,
        }
        self._total_usd += cost_usd
        self._compute_hours += hours
        self._append(event)
        self._check_cap()
        return event

    def _check_cap(self) -> None:
        if self._total_usd > self.hard_cap_usd:
            self._append(
                {
                    "schema_version": "1.0.0",
                    "recorded_at_utc": datetime.now(UTC).isoformat(),
                    "kind": "budget_cap_exceeded",
                    "hard_cap_usd": self.hard_cap_usd,
                    "total_usd_at_cap": round(self._total_usd, 4),
                }
            )
            raise BudgetExceededError(
                f"hard budget cap exceeded: ${self._total_usd:.2f} > "
                f"${self.hard_cap_usd:.2f}; run halted fail-closed "
                "(verify costs/cost_events.jsonl)"
            )

    def _check_warn(self) -> None:
        if not self._warned and self._total_usd > self.hard_cap_usd * self.warn_fraction:
            self._warned = True
            self._append(
                {
                    "schema_version": "1.0.0",
                    "recorded_at_utc": datetime.now(UTC).isoformat(),
                    "kind": "budget_warning",
                    "fraction": self.warn_fraction,
                }
            )

    def _append(self, event: dict[str, Any]) -> None:
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")

    def summary(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "total_usd": round(self._total_usd, 4),
            "api_usd": round(self._api_usd, 4),
            "compute_hours": round(self._compute_hours, 3),
            "api_calls_metered": self._calls,
            "hard_cap_usd": self.hard_cap_usd,
            "cap_headroom_usd": round(self.hard_cap_usd - self._total_usd, 4),
        }

    def write_summary(self) -> dict[str, Any]:
        summary = self.summary()
        target = self.directory / "summary.json"
        tmp = self.directory / ".summary.tmp"
        tmp.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(target)
        return summary


__all__ = ["CostLedger"]
