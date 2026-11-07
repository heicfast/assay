"""Coordinated-disclosure register (90-day windows, Project-Zero style).

A novel-attack finding is recorded as a HASH of its description until the
window closes or the affected lab ships a fix — the public log never
carries the working details. Publishing before resolution/expiry raises
DisclosureError (fail closed).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ..errors import DisclosureError
from ..ids import sha256_text

WINDOW_DAYS = 90


class NovelAttackRegister:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: dict[str, dict] = {}
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    entry = json.loads(line)
                    self._entries[entry["finding_id"]] = entry

    def register(
        self,
        description: str,
        affected_labs: list[str],
        *,
        discovered_at: datetime | None = None,
        evidence_ref: str = "",
    ) -> dict[str, Any]:
        discovered = discovered_at or datetime.now(UTC)
        finding_id = sha256_text(description)[:24]
        if finding_id in self._entries:
            raise DisclosureError(f"finding {finding_id} already registered")
        entry = {
            "finding_id": finding_id,
            "description_sha256": sha256_text(description),
            "affected_labs": affected_labs,
            "discovered_at_utc": discovered.isoformat(),
            "window_ends_at_utc": (discovered + timedelta(days=WINDOW_DAYS)).isoformat(),
            "status": "open",
            "evidence_ref": evidence_ref,
        }
        self._entries[finding_id] = entry
        self._append(entry)
        return {
            **entry,
            "instruction": "store the full description offline; "
            "only its hash is public until the window closes",
        }

    def mark_notified(self, finding_id: str) -> None:
        self._mutate(finding_id, "notified")

    def mark_resolved(self, finding_id: str) -> None:
        self._mutate(finding_id, "resolved")

    def publish(self, finding_id: str) -> dict[str, Any]:
        entry = self._entries.get(finding_id)
        if entry is None:
            raise DisclosureError(f"unknown finding {finding_id}")
        window_end = datetime.fromisoformat(entry["window_ends_at_utc"])
        if entry["status"] != "resolved" and datetime.now(UTC) < window_end:
            raise DisclosureError(
                f"finding {finding_id}: window open until {entry['window_ends_at_utc']} "
                "and not resolved — publishing refused (90-day policy)"
            )
        self._mutate(finding_id, "published")
        return {"finding_id": finding_id, "published_at_utc": datetime.now(UTC).isoformat()}

    def _mutate(self, finding_id: str, status: str) -> None:
        if finding_id not in self._entries:
            raise DisclosureError(f"unknown finding {finding_id}")
        self._entries[finding_id]["status"] = status
        self._rewrite()

    def _append(self, entry: dict) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")

    def _rewrite(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(
            "\n".join(
                json.dumps(e, sort_keys=True)
                for e in sorted(self._entries.values(), key=lambda e: e["finding_id"])
            )
            + "\n",
            encoding="utf-8",
        )
        tmp.replace(self.path)


NOTIFICATION_TEMPLATE = """\
To the {lab} safety team,

While running an independent red-team evaluation (ASSAY; coordinated
disclosure policy: 90 days), we identified an attack pattern that appears
to affect {model_line}. A full description and reproducible evidence are
available on request (finding {finding_id}).

Our window closes on {window_end}. We will not publish details before then
or before you ship a fix, whichever comes first.

— ASSAY Research
"""


__all__ = ["NovelAttackRegister", "WINDOW_DAYS", "NOTIFICATION_TEMPLATE"]
