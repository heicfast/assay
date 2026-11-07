"""Upstream fetch + parse + battery assembly (fail closed at every step).

The loader NEVER invents data: missing cache, wrong hash, unparsable file,
or a license/revision that cannot be recorded all raise typed errors that
stop the run. Fetched files are cached under ``data/cache`` (gitignored);
the repo ships no behavior text.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from ..errors import AssayError, RegistryError
from ..registry.behaviors import get_behavior_set
from .model import Behavior, make_behavior
from .splits import build_split_manifest


class FetchRecord(dict):
    """One upstream fetch: repo, revision, path, hash, license, date."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_upstream(
    set_id: str, cache_dir: str | Path, pin_revision: str | None = None
) -> FetchRecord:
    """Clone (or reuse) the upstream repo, copy the canonical file into cache.

    Records revision (pinned or resolved-at-fetch), file SHA-256, license,
    and date in the fetch manifest. A mismatched cached hash is a hard
    error — never a silent reuse.
    """
    spec = get_behavior_set(set_id)
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    work = cache / f"upstream-{set_id}"
    target = cache / f"{set_id}.source"
    if not work.exists():
        result = subprocess.run(
            ["git", "clone", "--quiet", spec.upstream_repo, str(work)],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            raise RegistryError(
                f"fetch {set_id}: clone failed ({result.stderr.strip()[:200]})", set_id=set_id
            )
    if pin_revision:
        result = subprocess.run(
            ["git", "-C", str(work), "checkout", "--quiet", pin_revision],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RegistryError(f"fetch {set_id}: cannot pin {pin_revision}", set_id=set_id)
    rev = subprocess.run(
        ["git", "-C", str(work), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    )
    revision = rev.stdout.strip()
    source = work / spec.upstream_path
    candidates = [source] + list(work.glob(spec.upstream_path.rsplit("/", 1)[-1]))
    source = next((p for p in candidates if p.is_file()), None)  # type: ignore[assignment]
    if source is None:
        raise RegistryError(
            f"fetch {set_id}: canonical file not found (hint {spec.upstream_path!r}); "
            "verify the upstream layout and update the registry hint",
            set_id=set_id,
        )
    target.write_bytes(source.read_bytes())
    record = FetchRecord(
        set_id=set_id,
        upstream_repo=spec.upstream_repo,
        revision=revision,
        pinned=pin_revision is not None,
        path=spec.upstream_path,
        file_sha256=_sha256_file(target),
        bytes=target.stat().st_size,
        license=spec.license_name,
        fetched_at_utc=datetime.now(UTC).isoformat(),
    )
    manifest_path = cache / f"{set_id}.fetch.json"
    manifest_path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    return record


def _load_cached(set_id: str, cache_dir: str | Path) -> tuple[Path, FetchRecord]:
    cache = Path(cache_dir)
    target = cache / f"{set_id}.source"
    manifest_path = cache / f"{set_id}.fetch.json"
    if not target.is_file() or not manifest_path.is_file():
        raise RegistryError(
            f"{set_id}: behavior cache missing — run `assay behaviors fetch` first "
            "(fail closed; never fabricate battery content)",
            set_id=set_id,
        )
    record = FetchRecord(json.loads(manifest_path.read_text(encoding="utf-8")))
    if _sha256_file(target) != record.get("file_sha256"):
        raise AssayError(
            f"{set_id}: cached battery file hash mismatch — refetch",
            set_id=set_id,
            kind="evidence_error",
        )
    return target, record


def parse_set(set_id: str, path: Path) -> list[Behavior]:
    """Parse a canonical upstream file into raw behaviors (split later)."""
    spec = get_behavior_set(set_id)
    rows: list[Behavior] = []
    if spec.format == "harmbench_csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                behavior = (row.get("Behavior") or "").strip()
                category = (row.get("Category") or "uncategorized").strip()
                split = (row.get("Split") or "standard").strip().lower()
                if not behavior or split != "standard":
                    continue
                rows.append(make_behavior(set_id, len(rows), behavior, category))
    elif spec.format == "jbb_json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        items = payload if isinstance(payload, list) else payload.get("behaviors", [])
        for item in items:
            if isinstance(item, dict):
                goal = (item.get("Goal") or item.get("goal") or "").strip()
                category = item.get("Category") or item.get("category") or "uncategorized"
            else:
                goal, category = str(item), "uncategorized"
            if goal:
                rows.append(make_behavior(set_id, len(rows), goal, str(category)))
    elif spec.format == "xstest_csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                prompt = (row.get("prompt") or row.get("Prompt") or "").strip()
                btype = (row.get("type") or row.get("Type") or "uncategorized").strip()
                if prompt:
                    rows.append(make_behavior(set_id, len(rows), prompt, btype))
    elif spec.format == "multi_jail_json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        items = payload if isinstance(payload, list) else payload.get("data", [])
        languages = ["sw", "th", "gu", "bn", "ta", "tel"]
        for item in items:
            en = (item.get("en") or "").strip()
            if not en:
                continue
            base = len(rows)
            rows.append(make_behavior(set_id, base, en, "multilingual_en"))
            for lang in languages:
                text = (item.get(lang) or "").strip()
                if text:
                    rows.append(
                        make_behavior(
                            set_id,
                            base + 1 + languages.index(lang),
                            text,
                            "multilingual",
                            language=lang,
                        )
                    )
    else:  # pragma: no cover - registry formats are exhaustive
        raise RegistryError(f"{set_id}: unknown format {spec.format}", set_id=set_id)
    if not rows:
        raise RegistryError(
            f"{set_id}: parsed zero behaviors — upstream format changed?", set_id=set_id
        )
    return rows


def cap_battery(
    behaviors: list[Behavior], *, max_per_set: int, per_category_cap: int, seed: int
) -> list[Behavior]:
    """Deterministic downsampling: per-category cap first, then set cap.

    Per-cluster seeds are derived from a CONTENT hash of the cluster name —
    NEVER Python's salted ``hash()`` — so the same battery caps identically
    in every process (PYTHONHASHSEED cannot touch us).
    """
    from ..ids import sha256_text

    by_cluster: dict[str, list[Behavior]] = {}
    for behavior in behaviors:
        by_cluster.setdefault(behavior.cluster, []).append(behavior)
    kept: list[Behavior] = []
    for cluster in sorted(by_cluster):
        group = sorted(by_cluster[cluster], key=lambda b: b.behavior_id)
        cluster_seed = seed + int(sha256_text(cluster)[:12], 16)
        rng = random.Random(cluster_seed)
        if len(group) > per_category_cap:
            group = rng.sample(group, per_category_cap)
        kept.extend(group)
    if len(kept) > max_per_set:
        rng = random.Random(seed)
        kept = rng.sample(sorted(kept, key=lambda b: b.behavior_id), max_per_set)
    return sorted(kept, key=lambda b: b.behavior_id)


def load_battery(plan, cache_dir: str | Path) -> dict:
    """Assemble the full battery: fetch-verified parses, caps, frozen splits.

    ``synthetic_demo`` is the smoke/test battery: generated in-process from
    obviously-fictional prompts (admissible only at smoke stages; NF-2).
    """
    from .synthetic import synthetic_battery

    all_behaviors: list[Behavior] = []
    fetch_records: list[dict] = []
    demo_sets = ("synthetic_demo", "synthetic_demo_benign")
    if any(s in (plan.harmful_sets + plan.benign_sets) for s in demo_sets):
        demo = synthetic_battery(24, 16)
        harmful_demo = [b for b in demo if b.set_id == "synthetic_demo"]
        benign_demo = [b for b in demo if b.set_id == "synthetic_demo_benign"]
        if "synthetic_demo" in plan.harmful_sets:
            all_behaviors.extend(harmful_demo)
        if "synthetic_demo_benign" in plan.benign_sets:
            all_behaviors.extend(benign_demo)
        fetch_records.append(
            {
                "set_id": "synthetic_demo",
                "license": "in-repo synthetic",
                "revision": "generated",
                "pinned": True,
            }
        )
    for set_id in [s for s in plan.harmful_sets + plan.benign_sets if s not in demo_sets]:
        try:
            _path, record = _load_cached(set_id, cache_dir)
        except RegistryError:
            fetched = fetch_upstream(set_id, cache_dir)
            _path, record = _load_cached(set_id, cache_dir)
            fetch_records.append(dict(fetched))
        if record not in fetch_records:
            fetch_records.append(dict(record))
        rows = parse_set(set_id, _path)
        rows = cap_battery(
            rows,
            max_per_set=plan.max_behaviors_per_set,
            per_category_cap=plan.per_category_cap,
            seed=plan.split_seed,
        )
        all_behaviors.extend(rows)
    behavior_rows = [{**b.to_payload(), "cluster": b.cluster} for b in all_behaviors]
    split_manifest = build_split_manifest(behavior_rows, plan.split_fractions, plan.split_seed)
    roles = {a["behavior_id"]: a["role"] for a in split_manifest["assignments"]}
    final = [
        Behavior(
            behavior_id=b.behavior_id,
            set_id=b.set_id,
            index=b.index,
            text=b.text,
            category=b.category,
            language=b.language,
            split_role=roles.get(b.behavior_id, "development"),
        )
        for b in all_behaviors
    ]
    return {
        "behaviors": final,
        "fetch_records": fetch_records,
        "split_manifest": split_manifest,
        "counts": {
            "total": len(final),
            "harmful": sum(1 for b in final if b.set_id not in plan.benign_sets),
            "benign": sum(1 for b in final if b.set_id in plan.benign_sets),
            "by_role": {
                role: sum(1 for b in final if b.split_role == role)
                for role in ("development", "validation", "holdout", "shift")
            },
        },
    }


__all__ = ["fetch_upstream", "parse_set", "cap_battery", "load_battery", "FetchRecord"]
