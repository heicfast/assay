"""Canonical hashing and opaque identifiers.

Every record in the evidence chain derives its identity from these
functions, so they are deliberately tiny, dependency-free, and covered by
byte-exactness tests.

Rules:
* identifiers are OPAQUE — they never encode outcomes, labels, splits, or
  attack/ benign status (a leaky id would label every record it names).
* canonical JSON uses sorted keys, no whitespace, ensure_ascii=False —
  the same object always hashes to the same bytes on every platform.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(payload: Any) -> str:
    """Deterministic JSON serialization used by every hash in the chain."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    """SHA-256 of the UTF-8 bytes of ``text``."""
    return sha256_bytes(text.encode("utf-8"))


def sha256_json(payload: Any) -> str:
    """SHA-256 of the canonical JSON of ``payload``."""
    return sha256_text(canonical_json(payload))


def digest_id(prefix: str, *parts: Any, length: int = 24) -> str:
    """Opaque id: ``<prefix>-<hex>`` over the canonical JSON of ``parts``.

    The digest is truncated (collision risk at 2^96 is irrelevant for
    record-level identity in one study) and carries NO semantics: the same
    inputs always derive the same id, and nothing about the id reveals
    what the parts contained.
    """
    digest = hashlib.sha256(canonical_json(list(parts)).encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:length]}"


def trial_id(
    run_id: str,
    model_id: str,
    attack_id: str,
    behavior_id: str,
    seed: int,
    variant: str,
) -> str:
    """Identity of one planned trial (model x attack x behavior x seed x variant)."""
    return digest_id("tr", run_id, model_id, attack_id, behavior_id, seed, variant)


def verdict_id(trial: str, judge_id: str) -> str:
    """Identity of one judge verdict record."""
    return digest_id("vd", trial, judge_id)


def turn_id(trial: str, index: int) -> str:
    """Identity of one model turn within a trial."""
    return digest_id("tn", trial, index)


_LABEL_WORDS = (
    "attack",
    "attacked",
    "honest",
    "benign",
    "harmful",
    "refuse",
    "refused",
    "comply",
    "complied",
    "jailbreak",
    "jailbroken",
    "victim",
    "guilty",
    "positive",
    "negative",
    "success",
    "succeeded",
    "failed",
    "dev",
    "val",
    "development",
    "validation",
    "holdout",
    "shift",
    "test",
    "train",
)


def is_opaque_identifier(value: str) -> bool:
    """An identifier is opaque iff it is exactly ``<alpha>-<hex[24]>`` AND its
    prefix carries no label semantics: a hand-crafted ``attack-<hex>`` fails
    the audit even though the format matches.
    """
    if not value or "-" not in value:
        return False
    prefix, _, tail = value.rpartition("-")
    if not prefix or not tail:
        return False
    if prefix.lower() in _LABEL_WORDS:
        return False
    if not all(ch.isascii() and (ch.isalnum() or ch == "_") for ch in prefix):
        return False
    try:
        int(tail, 16)
    except ValueError:
        return False
    return len(tail) == 24


__all__ = [
    "canonical_json",
    "sha256_bytes",
    "sha256_text",
    "sha256_json",
    "digest_id",
    "trial_id",
    "verdict_id",
    "turn_id",
    "is_opaque_identifier",
]
