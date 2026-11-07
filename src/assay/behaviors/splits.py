"""Frozen behavior splits — cluster-scoped, deterministic, hash-pinned.

WHOLE CLUSTERS are assigned to split roles (never individual behaviors):
behaviors within a category are near-duplicates, so splitting inside a
cluster would leak development material into holdout. The assignment is a
pure function of (sorted cluster list, fractions, seed) and is recorded in
a manifest whose hash goes into every run manifest.
"""

from __future__ import annotations

import random
from typing import Literal, TypedDict

from ..ids import sha256_json

SplitRole = Literal["development", "validation", "holdout", "shift"]
SPLIT_ROLES: tuple[SplitRole, ...] = ("development", "validation", "holdout", "shift")


class SplitAssignment(TypedDict):
    behavior_id: str
    cluster: str
    role: SplitRole


def assign_clusters(
    clusters: list[str],
    fractions: dict[str, float],
    seed: int,
) -> dict[str, SplitRole]:
    """Deterministically map whole clusters onto split roles.

    Clusters are shuffled with a seeded RNG, then filled into roles in the
    fixed role order (development, validation, holdout, shift) by target
    share. Small remainders go to development (the only role that may
    absorb extras without touching evaluation roles).
    """
    if set(fractions) != set(SPLIT_ROLES):
        raise ValueError(f"fractions must cover all four roles: {SPLIT_ROLES}")
    total = sum(fractions.values())
    if not 0.99 <= total <= 1.01:
        raise ValueError("split fractions must sum to ~1.0")
    ordered = sorted(clusters)
    rng = random.Random(seed)
    rng.shuffle(ordered)
    assignment: dict[str, SplitRole] = {}
    start = 0
    for role in SPLIT_ROLES:
        share = fractions[role] / total
        count = round(len(ordered) * share)
        for cluster in ordered[start : start + count]:
            assignment[cluster] = role
        start += count
    for cluster in ordered[start:]:  # remainder -> development
        assignment[cluster] = "development"
    return assignment


def build_split_manifest(
    behavior_rows: list[dict],
    fractions: dict[str, float],
    seed: int,
) -> dict:
    """Build the frozen split manifest from behavior payload rows."""
    clusters = sorted({row["cluster"] for row in behavior_rows})
    if len(clusters) < len(SPLIT_ROLES):
        raise ValueError(
            f"need at least {len(SPLIT_ROLES)} clusters for a split; have {len(clusters)}"
        )
    cluster_roles = assign_clusters(clusters, fractions, seed)
    assignments = [
        SplitAssignment(
            behavior_id=row["behavior_id"],
            cluster=row["cluster"],
            role=cluster_roles[row["cluster"]],
        )
        for row in behavior_rows
    ]
    assignments.sort(key=lambda a: a["behavior_id"])
    payload = {
        "schema_version": "1.0.0",
        "split_seed": seed,
        "fractions": fractions,
        "cluster_roles": dict(sorted(cluster_roles.items())),
        "assignments": assignments,
    }
    payload["split_manifest_sha256"] = sha256_json(payload)
    return payload


__all__ = ["SplitRole", "SPLIT_ROLES", "assign_clusters", "build_split_manifest"]
