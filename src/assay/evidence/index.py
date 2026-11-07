"""Evidence index: every file in a run, enumerated and hashed.

Security rules inherited from the predecessor program's hardening reviews:
symlinks are refused loudly; UNINDEXED files are problems by name (reverse
enumeration — a decoy cannot escape coverage); the files array is in
canonical sorted order; metadata is bound to the run manifest.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..ids import sha256_json

EXCLUDED = {
    "artifacts/checksums.sha256",
    "artifacts/evidence_index.json",
    "run_manifest.json",
    "journal.jsonl",
}
TRANSIENT_SUFFIXES = (".tmp", ".lock")


def _role(relative: str) -> str:
    top = relative.split("/", 1)[0]
    return {
        "trials": "trial_envelope",
        "privileged": "privileged_raw_inference",
        "verdicts": "judge_measurement",
        "labels": "human_ground_truth",
        "transactions": "write_ahead_transaction",
        "commits": "transaction_commit_marker",
        "plan": "frozen_plan",
        "battery": "battery_manifest",
        "costs": "cost_ledger",
        "reports": "derived_analysis",
        "figures": "derived_visualization",
        "tables": "derived_table",
    }.get(top, "run_metadata")


def _media_type(path: Path) -> str:
    return {
        ".jsonl": "application/x-ndjson",
        ".json": "application/json",
        ".sha256": "text/x-checksum-sha256",
        ".csv": "text/csv",
        ".md": "text/markdown",
        ".png": "image/png",
        ".pdf": "application/pdf",
    }.get(path.suffix, "application/octet-stream")


def _scan(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    files: list[dict[str, Any]] = []
    problems: list[str] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            problems.append(f"symlink in run directory: {relative}")
            continue
        if not path.is_file():
            continue
        if relative in EXCLUDED or relative.endswith(TRANSIENT_SUFFIXES):
            continue
        if relative.startswith("costs/"):
            continue  # ledger integrity is checked by its own replay
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        files.append(
            {
                "path": relative,
                "role": _role(relative),
                "bytes": path.stat().st_size,
                "sha256": digest.hexdigest(),
                "media_type": _media_type(path),
            }
        )
    return files, problems


def build_evidence_index(run_dir: str | Path) -> dict[str, Any]:
    root = Path(run_dir).resolve()
    manifest = json.loads((root / "run_manifest.json").read_text(encoding="utf-8"))
    files, problems = _scan(root)
    if problems:
        raise ValueError("; ".join(problems))
    payload = {
        "schema_version": "1.0.0",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "run_id": manifest.get("run_id"),
        "stage": manifest.get("stage"),
        "config_sha256": manifest.get("config_sha256"),
        "code_revision": manifest.get("code_revision"),
        "file_count": len(files),
        "total_bytes": sum(f["bytes"] for f in files),
        "files": files,
    }
    payload["content_sha256"] = sha256_json(files)
    payload["index_sha256"] = sha256_json({k: v for k, v in payload.items() if k != "index_sha256"})
    target = root / "artifacts" / "evidence_index.json"
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(target)
    return payload


def verify_evidence_index(run_dir: str | Path) -> dict[str, Any]:
    root = Path(run_dir).resolve()
    path = root / "artifacts" / "evidence_index.json"
    if not path.is_file():
        return {"ok": False, "problems": ["evidence index missing"]}
    payload = json.loads(path.read_text(encoding="utf-8"))
    problems: list[str] = []
    claimed = payload.pop("index_sha256", None)
    if claimed != sha256_json(
        {k: v for k, v in payload.items() if k != "content_sha256"}
    ) and claimed != sha256_json(payload):
        problems.append("evidence index self-digest mismatch")
    files = payload.get("files", [])
    if payload.get("content_sha256") != sha256_json(files):
        problems.append("evidence content digest mismatch")
    paths = [f["path"] for f in files]
    if paths != sorted(paths):
        problems.append("files not in canonical sorted order")
    manifest_path = root / "run_manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for field in ("run_id", "config_sha256"):
            if payload.get(field) != manifest.get(field):
                problems.append(f"index metadata not bound to run manifest: {field}")
    indexed = set(paths)
    for f in files:
        target = root / f["path"]
        if not target.is_file():
            problems.append(f"indexed file missing: {f['path']}")
            continue
        digest = hashlib.sha256()
        with target.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        if digest.hexdigest() != f["sha256"]:
            problems.append(f"indexed digest mismatch: {f['path']}")
    # reverse enumeration: every real file must be indexed
    for real in sorted(root.rglob("*")):
        relative = real.relative_to(root).as_posix()
        if real.is_symlink():
            problems.append(f"symlink in run directory: {relative}")
            continue
        if not real.is_file():
            continue
        if relative in EXCLUDED or relative.endswith(TRANSIENT_SUFFIXES):
            continue
        if relative.startswith("costs/"):
            continue
        if relative not in indexed:
            problems.append(f"unindexed file present: {relative}")
    return {"ok": not problems, "files_checked": len(files), "problems": problems[:100]}


__all__ = ["build_evidence_index", "verify_evidence_index"]
