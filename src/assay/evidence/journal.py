"""Hash-chained append-only event journal.

Every event hashes its predecessor: a tampered or deleted event breaks the
chain and verification fails. Locking uses a PID file — a stale lock (dead
holder) is recoverable; a live one is refused.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..ids import sha256_json


class Journal:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._chain_head: str = "genesis"
        if self.path.exists():
            lines = [
                line for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()
            ]
            if lines:
                self._chain_head = str(json.loads(lines[-1])["event_sha256"])

    def append(self, kind: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        event = {
            "kind": kind,
            "payload": payload or {},
            "recorded_at_utc": datetime.now(UTC).isoformat(),
            "previous_event_sha256": self._chain_head,
        }
        event["event_sha256"] = sha256_json(event)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self._chain_head = str(event["event_sha256"])
        return event

    def events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [
            json.loads(line)
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    @classmethod
    def verify_chain(cls, events: list[dict[str, Any]]) -> list[str]:
        problems: list[str] = []
        head = "genesis"
        for index, event in enumerate(events):
            candidate = dict(event)
            candidate.pop("event_sha256", None)
            candidate.pop("recorded_at_utc", None)
            if sha256_json(candidate) != event.get("event_sha256"):
                problems.append(f"event {index}: hash mismatch")
            if event.get("previous_event_sha256") != head:
                problems.append(f"event {index}: chain break")
            head = str(event.get("event_sha256"))
        return problems


class RunLock:
    """PID-file lock: stale locks recoverable, live locks refused."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def acquire(self) -> bool:
        import errno

        if self.path.exists():
            try:
                pid = int(self.path.read_text(encoding="utf-8").strip())
            except ValueError:
                pid = -1
            try:
                os.kill(pid, 0)
            except OSError as exc:
                if exc.errno == errno.ESRCH:
                    self.path.unlink(missing_ok=True)  # stale holder: recover
                else:
                    return False
            else:
                return False
        self.path.write_text(str(os.getpid()), encoding="utf-8")
        return True

    def release(self) -> None:
        self.path.unlink(missing_ok=True)


__all__ = ["Journal", "RunLock"]
