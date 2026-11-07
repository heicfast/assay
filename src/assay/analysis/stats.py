"""Inference machinery: cluster bootstrap, Holm/BH, TOST, exact tests."""

from __future__ import annotations

import random


def cluster_bootstrap_proportion(
    data: list[tuple[str, bool, bool]],
    *,
    value_index: int,
    replicates: int = 2000,
    confidence_level: float = 0.95,
    seed: int = 20261107,
    min_total_clusters_for_ci: int = 8,
    max_degenerate_fraction_for_ci: float = 0.10,
) -> dict:
    """Bootstrap a proportion with the CLUSTER as the resampling unit.

    ``data`` rows are (cluster, flag_a, flag_b); ``value_index`` selects the
    flag being estimated. Degenerate replicates (empty cluster draw) are
    counted, never dropped silently. CIs carry eligibility gates.
    """
    clusters: dict[str, list[tuple]] = {}
    for row in data:
        clusters.setdefault(row[0], []).append(row)
    keys = sorted(clusters)
    if not keys:
        return {"estimate": None, "ci_low": None, "ci_high": None, "error": "no_data"}

    def proportion(rows: list[tuple]) -> float | None:
        if not rows:
            return None
        hits = sum(1 for r in rows if r[value_index])
        return hits / len(rows)

    point = proportion(data)
    rng = random.Random(seed)
    values: list[float] = []
    degenerate = 0
    for _ in range(replicates):
        sample: list[tuple] = []
        for _key in range(len(keys)):
            sample.extend(clusters[rng.choice(keys)])
        value = proportion(sample)
        if value is None:
            degenerate += 1
            continue
        values.append(value)
    if not values:
        return {
            "estimate": point,
            "ci_low": None,
            "ci_high": None,
            "error": "all_replicates_degenerate",
        }
    values.sort()
    alpha = 1.0 - confidence_level
    reasons: list[str] = []
    if len(keys) < min_total_clusters_for_ci:
        reasons.append("too_few_clusters")
    if degenerate / replicates > max_degenerate_fraction_for_ci:
        reasons.append("too_many_degenerate_replicates")
    lo = values[int(alpha / 2 * len(values))]
    hi = values[min(len(values) - 1, int((1 - alpha / 2) * len(values)))]
    return {
        "estimate": round(point, 4) if point is not None else None,
        "ci_low": None if reasons else round(lo, 4),
        "ci_high": None if reasons else round(hi, 4),
        "ci_status": "not_estimable" if reasons else "estimable",
        "ci_ineligibility_reasons": reasons,
        "n_clusters": len(keys),
        "n": len(data),
        "replicates": replicates,
        "degenerate_replicates": degenerate,
        "confidence_level": confidence_level,
        "seed": seed,
    }


def holm(p_values: list[float]) -> list[float]:
    if any(not 0.0 <= p <= 1.0 for p in p_values):
        raise ValueError("p-values must be in [0, 1]")
    ordered = sorted(enumerate(p_values), key=lambda item: item[1])
    adjusted = [0.0] * len(ordered)
    running = 0.0
    count = len(ordered)
    for rank, (original_index, value) in enumerate(ordered):
        running = max(running, min(1.0, (count - rank) * value))
        adjusted[original_index] = running
    return adjusted


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    count = len(p_values)
    if count == 0:
        return []
    ordered = sorted(enumerate(p_values), key=lambda item: item[1])
    adjusted = [0.0] * count
    running = 1.0
    for rank in range(count - 1, -1, -1):
        original_index, value = ordered[rank]
        running = min(running, value * count / (rank + 1), 1.0)
        adjusted[original_index] = running
    return adjusted


def tost_on_bootstrap(
    bootstrap_values: list[float], *, sesoi: float, confidence_level: float = 0.95
) -> dict:
    """Equivalence (TOST) on the bootstrap replicate distribution: the
    (1-2a) interval must lie inside +/- SESOI. Licenses bounded negatives;
    a nonsignificant superiority test never can."""
    if not bootstrap_values:
        return {"verdict": "not_estimable", "sesoi": sesoi}
    alpha = 1.0 - confidence_level
    values = sorted(bootstrap_values)
    lo = values[int(alpha * len(values))]
    hi = values[min(len(values) - 1, int((1 - alpha) * len(values)))]
    inside = (-sesoi <= lo) and (hi <= sesoi)
    return {
        "verdict": "equivalent_within_sesoi" if inside else "not_equivalent",
        "interval": (round(lo, 4), round(hi, 4)),
        "sesoi": sesoi,
        "confidence_level": confidence_level,
    }


def exact_mcnemar(a: list[bool], b: list[bool]) -> dict:
    if len(a) != len(b):
        raise ValueError("paired vectors must be equal length")
    import math

    only_a = sum(1 for x, y in zip(a, b, strict=True) if x and not y)
    only_b = sum(1 for x, y in zip(a, b, strict=True) if y and not x)
    discordant = only_a + only_b
    if discordant == 0:
        p_value = 1.0
    else:
        tail = sum(math.comb(discordant, k) for k in range(0, min(only_a, only_b) + 1)) / (
            2**discordant
        )
        p_value = min(1.0, 2.0 * tail)
    return {
        "only_a": only_a,
        "only_b": only_b,
        "discordant": discordant,
        "p_value_two_sided": round(p_value, 6),
        "method": "exact_mcnemar_conditional_binomial",
    }


def spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 3:
        return None

    def _ranks(values: list[float]) -> list[float]:
        order = sorted(range(len(values)), key=lambda i: values[i])
        ranks = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
                j += 1
            avg = (i + 1 + j + 1) / 2.0
            for k in range(i, j + 1):
                ranks[order[k]] = avg
            i = j + 1
        return ranks

    rx, ry = _ranks(xs), _ranks(ys)
    return pearson(rx, ry)


def pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    var_x = sum((x - mx) ** 2 for x in xs)
    var_y = sum((y - my) ** 2 for y in ys)
    denom = (var_x * var_y) ** 0.5
    if denom == 0:
        return None
    return round(cov / denom, 4)


__all__ = [
    "cluster_bootstrap_proportion",
    "holm",
    "benjamini_hochberg",
    "tost_on_bootstrap",
    "exact_mcnemar",
    "spearman",
    "pearson",
]
