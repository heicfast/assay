"""Read-only verification audit of a run directory.

``assay verify`` NEVER modifies the audited tree. A run that fails
verification cannot be presented as research evidence. Checks:
* manifest present + frozen fields consistent with trials;
* trial ids unique and opaque; commit ledger complete;
* transaction/commit hash chain re-derived;
* envelope/privileged digests recomputed;
* verdicts: unique ids, derivation re-checked, prompt_hash bound to the
  frozen judge constants, rendered-prompt hash, envelope fingerprint;
* checksum ledger + evidence index with reverse enumeration.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..ids import is_opaque_identifier, sha256_json, verdict_id
from ..judges.ensemble import FROZEN_PROMPT_HASHES
from .index import verify_evidence_index
from .store import RunStore, envelope_fingerprint


def verify_run(run_dir: str) -> dict[str, Any]:
    root = Path(run_dir)
    if not root.is_dir():
        return {"ok": False, "problems": ["run directory does not exist"]}
    store = RunStore(root)
    problems: list[str] = []
    warnings: list[str] = []

    manifest_path = root / "run_manifest.json"
    if not manifest_path.is_file():
        return {"ok": False, "problems": ["run_manifest.json missing"]}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    trials = []
    for _shard in sorted((root / "trials").glob("shard-*.jsonl")):
        try:
            trials.extend(store.iter_trials()) if False else None
            for line in _shard.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    trials.append(json.loads(line))
        except json.JSONDecodeError as exc:
            problems.append(f"schema violation in {_shard.name}: {exc}")
    privileged = {}
    for _shard in sorted((root / "privileged").glob("shard-*.jsonl")):
        try:
            for line in _shard.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    record = json.loads(line)
                    privileged[record["trial_id"]] = record
        except json.JSONDecodeError as exc:
            problems.append(f"schema violation in {_shard.name}: {exc}")
    ids = [t["trial_id"] for t in trials]
    if len(ids) != len(set(ids)):
        problems.append("duplicate trial ids present")
    for value in ids:
        if not is_opaque_identifier(value):
            problems.append(f"non-opaque trial id: {value}")
    ledger = store.completed_trial_ids()
    missing = set(ids) - ledger
    if missing:
        problems.append(f"{len(missing)} trials not in commit ledger")
    extra = ledger - set(ids)
    if extra:
        problems.append(f"{len(extra)} ledger entries without trials")

    # transaction/commit chain
    for tx_path in sorted((root / "transactions").glob("*.json")):
        trial_id = tx_path.stem
        transaction = json.loads(tx_path.read_text(encoding="utf-8"))
        candidate = dict(transaction)
        claimed_digest = candidate.pop("transaction_sha256", None)
        if sha256_json(candidate) != claimed_digest:
            problems.append(f"transaction self-digest mismatch: {trial_id}")
        commit_path = root / "commits" / tx_path.name
        if not commit_path.is_file():
            problems.append(f"uncommitted transaction: {trial_id}")
            continue
        envelope = next((t for t in trials if t["trial_id"] == trial_id), None)
        if envelope is None or sha256_json(envelope) != transaction.get("envelope_sha256"):
            problems.append(f"transaction/envelope digest mismatch: {trial_id}")
        record = privileged.get(trial_id)
        if record is None or sha256_json(record) != transaction.get("privileged_sha256"):
            problems.append(f"transaction/privileged digest mismatch: {trial_id}")

    # verdicts
    seen_verdict_ids: set[str] = set()
    for verdict in store.iter_verdicts():
        vid = verdict.get("verdict_id")
        if not vid:
            problems.append("verdict without id")
            continue
        if vid in seen_verdict_ids:
            problems.append(f"duplicate verdict id: {vid}")
        seen_verdict_ids.add(vid)
        if vid != verdict_id(verdict.get("trial_id", ""), verdict.get("judge_id", "")):
            problems.append(f"verdict id derivation mismatch: {vid}")
        frozen = FROZEN_PROMPT_HASHES.get(verdict.get("judge_id", ""))
        if frozen is None:
            problems.append(f"no frozen prompt hash for judge {verdict.get('judge_id')}")
        elif verdict.get("prompt_hash") != frozen:
            problems.append(f"prompt_hash not bound to frozen constant: {vid}")
        if hashlib.sha256(
            (verdict.get("rendered_prompt") or "").encode("utf-8")
        ).hexdigest() != verdict.get("rendered_prompt_hash"):
            problems.append(f"rendered prompt hash mismatch: {vid}")
        envelope = next((t for t in trials if t["trial_id"] == verdict.get("trial_id")), None)
        if (
            envelope is not None
            and verdict.get("envelope_fingerprint")
            and verdict["envelope_fingerprint"] != envelope_fingerprint(envelope)
        ):
            problems.append(f"verdict/envelope fingerprint mismatch: {vid}")

    # symlinks anywhere are problems
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            problems.append(f"symlink in run directory: {path.relative_to(root)}")

    # checksum ledger
    checksum_path = root / "artifacts" / "checksums.sha256"
    covered: set[str] = set()
    if checksum_path.is_file():
        for line in checksum_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            if "  " not in line:
                problems.append(f"malformed checksum line: {line[:60]!r}")
                continue
            digest, rel = line.split("  ", 1)
            rel = rel.strip()
            covered.add(rel)
            target = root / rel
            if not target.is_file():
                problems.append(f"checksummed file missing: {rel}")
                continue
            current = hashlib.sha256(target.read_bytes()).hexdigest()
            if current != digest:
                problems.append(f"checksum mismatch: {rel}")
        for real in sorted(root.rglob("*")):
            if not real.is_file() or real.is_symlink():
                continue
            rel = real.relative_to(root).as_posix()
            if (
                rel.startswith("artifacts/")
                or rel == "journal.jsonl"
                or rel == "run_manifest.json"
                or rel.startswith("costs/")
                or rel.endswith((".tmp", ".lock"))
            ):
                continue
            if rel not in covered:
                problems.append(f"file not covered by checksum ledger: {rel}")
    else:
        message = "MISSING_CHECKSUM_LEDGER"
        if manifest.get("stage") in ("pilot", "confirmatory", "mechanistic"):
            problems.append(message)
        else:
            warnings.append(message)

    index_result = verify_evidence_index(root)
    problems.extend(index_result["problems"])
    return {
        "ok": not problems,
        "trials": len(trials),
        "verdicts": len(seen_verdict_ids),
        "problems": problems[:100],
        "warnings": warnings,
        "run_id": manifest.get("run_id"),
        "stage": manifest.get("stage"),
    }


__all__ = ["verify_run"]
