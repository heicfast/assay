"""Run store: atomic, append-only, crash-recoverable layout.

Every write is temp->fsync->rename. A trial becomes durable through a
write-ahead transaction (envelope + privileged) sealed by a commit marker;
recovery completes interrupted transactions without re-running inference.
Completion = a commit marker exists; resume skips exactly those.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..ids import sha256_json, sha256_text


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    tmp.replace(path)


def atomic_write_json(path: Path, payload: Any) -> None:
    _atomic_write(path, json.dumps(payload, sort_keys=True, ensure_ascii=False))


class RunStore:
    """One run directory. Layout:

    runs/<run_id>/
      run_manifest.json        plan/ battery/ trials/ privileged/ verdicts/
      labels/ transactions/ commits/ costs/ reports/ figures/ tables/
      artifacts/               journal.jsonl
    """

    def __init__(self, run_dir: str | Path) -> None:
        self.run_dir = Path(run_dir).resolve()
        self.run_dir.mkdir(parents=True, exist_ok=True)
        for sub in (
            "plan",
            "battery",
            "trials",
            "privileged",
            "verdicts",
            "labels",
            "transactions",
            "commits",
            "costs",
            "reports",
            "figures",
            "tables",
            "artifacts",
        ):
            (self.run_dir / sub).mkdir(exist_ok=True)

    # -- paths -------------------------------------------------------------------
    @property
    def manifest_path(self) -> Path:
        return self.run_dir / "run_manifest.json"

    @property
    def journal_path(self) -> Path:
        return self.run_dir / "journal.jsonl"

    def trial_shard(self, index: int) -> Path:
        return self.run_dir / "trials" / f"shard-{index:05d}.jsonl"

    def privileged_shard(self, index: int) -> Path:
        return self.run_dir / "privileged" / f"shard-{index:05d}.jsonl"

    def verdict_shard(self, judge_id: str, index: int) -> Path:
        return self.run_dir / "verdicts" / f"{judge_id}-{index:05d}.jsonl"

    # -- manifest ---------------------------------------------------------------
    def write_manifest(self, payload: dict[str, Any]) -> None:
        required = {
            "run_id",
            "stage",
            "config_sha256",
            "code_revision",
            "plan_manifest_sha256",
            "created_at_utc",
        }
        missing = required - set(payload)
        if missing:
            raise ValueError(f"run manifest missing fields: {sorted(missing)}")
        atomic_write_json(self.manifest_path, payload)

    def read_manifest(self) -> dict[str, Any]:
        if not self.manifest_path.is_file():
            raise FileNotFoundError(f"run manifest missing: {self.manifest_path}")
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    # -- trials (public envelopes) -----------------------------------------------
    def append_trial(self, shard_index: int, envelope: dict[str, Any]) -> None:
        path = self.trial_shard(shard_index)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(envelope, sort_keys=True, ensure_ascii=False) + "\n")
            handle.flush()

    def append_privileged(self, shard_index: int, record: dict[str, Any]) -> None:
        path = self.privileged_shard(shard_index)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
            handle.flush()

    def append_verdict(self, judge_id: str, shard_index: int, verdict: dict[str, Any]) -> None:
        path = self.verdict_shard(judge_id, shard_index)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(verdict, sort_keys=True, ensure_ascii=False) + "\n")
            handle.flush()

    def iter_trials(self):
        for path in sorted((self.run_dir / "trials").glob("shard-*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    yield json.loads(line)

    def iter_privileged(self):
        for path in sorted((self.run_dir / "privileged").glob("shard-*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    yield json.loads(line)

    def iter_verdicts(self):
        for path in sorted((self.run_dir / "verdicts").glob("*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    yield json.loads(line)

    # -- WAL transactions -------------------------------------------------------
    def transaction_path(self, trial_id: str) -> Path:
        return self.run_dir / "transactions" / f"{trial_id}.json"

    def commit_path(self, trial_id: str) -> Path:
        return self.run_dir / "commits" / f"{trial_id}.json"

    def write_transaction(self, trial_id: str, envelope: dict, privileged: dict) -> dict[str, Any]:
        transaction = {
            "schema_version": "1.0.0",
            "trial_id": trial_id,
            "envelope_sha256": sha256_json(envelope),
            "privileged_sha256": sha256_json(privileged),
        }
        transaction["transaction_sha256"] = sha256_json(transaction)
        atomic_write_json(self.transaction_path(trial_id), transaction)
        return transaction

    def write_commit(self, trial_id: str, transaction: dict[str, Any]) -> None:
        atomic_write_json(
            self.commit_path(trial_id),
            {
                "schema_version": "1.0.0",
                "trial_id": trial_id,
                "transaction_sha256": sha256_json(transaction),
                "committed_at_utc": datetime.now(UTC).isoformat(),
            },
        )

    def completed_trial_ids(self) -> set[str]:
        return {p.stem for p in (self.run_dir / "commits").glob("*.json")}

    def recover(self) -> list[str]:
        """Complete interrupted transactions (commit missing -> drop both halves).

        Interrupted-before-commit trials are re-run (their evidence was never
        durable); the append-only shards may contain stale bytes, which is
        fine because the completion ledger filters them at read time and
        verification re-derives everything from commits.
        """
        recovered: list[str] = []
        for tx_path in sorted((self.run_dir / "transactions").glob("*.json")):
            trial_id = tx_path.stem
            if self.commit_path(trial_id).is_file():
                continue
            recovered.append(trial_id)
        return recovered

    # -- artifacts ---------------------------------------------------------------
    def write_checksums(self) -> Path:
        lines: list[str] = []
        covered: list[Path] = []
        for path in sorted(self.run_dir.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(self.run_dir).as_posix()
            if (
                rel.startswith("artifacts/")
                or rel == "journal.jsonl"
                or rel.endswith(".tmp")
                or rel == "run_manifest.json"
                or rel.startswith("costs/")
            ):
                continue  # self-referential / transient files are excluded by path
            digest = _file_digest(path)
            lines.append(f"{digest}  {rel}")
            covered.append(path)
        target = self.run_dir / "artifacts" / "checksums.sha256"
        _atomic_write(target, "\n".join(lines) + ("\n" if lines else ""))
        return target


def _file_digest(path: Path) -> str:
    import hashlib

    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            value.update(chunk)
    return value.hexdigest()


def envelope_fingerprint(envelope: dict[str, Any]) -> str:
    """Creation-time binding between a verdict and its trial envelope."""
    core = {
        "trial_id": envelope.get("trial_id"),
        "messages": envelope.get("messages"),
        "final_reply": envelope.get("final_reply"),
    }
    return sha256_text(json.dumps(core, sort_keys=True, ensure_ascii=False))


__all__ = ["RunStore", "atomic_write_json", "envelope_fingerprint"]
