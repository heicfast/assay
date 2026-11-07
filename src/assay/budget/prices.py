"""Audited price table — single source of truth: the model registry.

API prices come from the registry entries (each carries source URL + date).
Compute prices are separate entries with the same verification discipline.
A price without a source+date is a config error (fail closed) — prices
drift, and an unverifiable number must never enter a budget.
"""

from __future__ import annotations

from typing import NamedTuple

from ..registry.models import PROFILES


class ComputePrice(NamedTuple):
    instance_type: str
    usd_per_hour_on_demand: float
    note: str
    source_url: str
    verified_at: str


# Verified 2026-11-06 (predecessor program's vetted pass, re-verified at launch):
COMPUTE_PRICES: dict[str, ComputePrice] = {
    "p4de.24xlarge": ComputePrice(
        instance_type="p4de.24xlarge",
        usd_per_hour_on_demand=27.447,
        note="8x A100-80GB, us-east-1 on-demand; spot historically 51-82% off",
        source_url="https://instances.vantage.sh/aws/ec2/p4de.24xlarge",
        verified_at="2026-11-06",
    ),
    # p5.48xlarge (8x H100-80GB) is region-priced and was NOT verifiable in the
    # research pass: it stays out of the table until verified at launch.
    # The calculator uses p4de as the reference compute line and reports the
    # p5 line as "requires verification" rather than inventing a number.
}


class PriceTable:
    """(provider, model_id) -> (input, output) USD per 1M tokens, from registry."""

    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], tuple[float, float]] = {}
        for profile in PROFILES:
            if profile.pricing is not None and profile.api is not None:
                provider = profile.lab.lower().replace(" ", "_")
                self._entries[(provider, profile.model_id)] = (
                    profile.pricing.input_usd_per_mtok,
                    profile.pricing.output_usd_per_mtok,
                )

    def lookup(self, provider: str, model_id: str) -> tuple[float, float] | None:
        return self._entries.get((provider, model_id))


def estimate_run_cost_usd(
    *, api_calls: list[tuple[str, str, int, int]], compute_hours_by_type: dict[str, float]
) -> dict:
    """Estimate a planned run's cost from (provider, model, ptok, ctok) tuples
    plus compute hours. Used by the planner and the budget simulator —
    an ESTIMATE, never a report: only the ledger's metered numbers are."""
    table = PriceTable()
    api_usd = 0.0
    unknown: list[str] = []
    for provider, model_id, ptok, ctok in api_calls:
        price = table.lookup(provider, model_id)
        if price is None:
            unknown.append(f"{provider}/{model_id}")
            continue
        api_usd += ptok * price[0] / 1e6 + ctok * price[1] / 1e6
    compute_usd = 0.0
    unverified_compute: list[str] = []
    for instance, hours in compute_hours_by_type.items():
        entry = COMPUTE_PRICES.get(instance)
        if entry is None:
            unverified_compute.append(instance)
            continue
        compute_usd += hours * entry.usd_per_hour_on_demand
    return {
        "api_usd": round(api_usd, 2),
        "compute_usd": round(compute_usd, 2),
        "total_usd": round(api_usd + compute_usd, 2),
        "unpriced_models": sorted(set(unknown)),
        "unverified_compute": sorted(set(unverified_compute)),
    }


__all__ = ["PriceTable", "COMPUTE_PRICES", "ComputePrice", "estimate_run_cost_usd"]
