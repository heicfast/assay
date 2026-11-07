"""Budget ledger, price discipline, disclosure windows, engine plan census."""

from __future__ import annotations

import json

import pytest

from assay.budget.ledger import BudgetExceededError, CostLedger
from assay.disclosure import NovelAttackRegister
from assay.errors import DisclosureError


def test_ledger_fails_closed_at_cap(tmp_path):
    ledger = CostLedger(tmp_path, hard_cap_usd=1.0)
    ledger.record(
        provider="openai",
        model_id="api/openai/gpt-6.1-terra",
        prompt_tokens=100_000,
        completion_tokens=100_000,
        price_per_mtok=(1.0, 5.0),
    )  # $0.60 < cap: admitted
    with pytest.raises(BudgetExceededError, match="fail-closed"):
        ledger.record(
            provider="openai",
            model_id="api/openai/gpt-6-luna",
            prompt_tokens=100_000,
            completion_tokens=100_000,
            price_per_mtok=(1.0, 5.0),
        )  # +$0.60 crosses the cap


def test_ledger_resume_does_not_reset_meter(tmp_path):
    first = CostLedger(tmp_path, hard_cap_usd=100.0)
    first.record(
        provider="deepseek",
        model_id="api/deepseek/deepseek-chat",
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
        price_per_mtok=(0.15, 0.6),
    )
    first.write_summary()
    resumed = CostLedger(tmp_path, hard_cap_usd=100.0)
    assert resumed.summary()["total_usd"] == first.summary()["total_usd"]


def test_compute_metering_counts_toward_cap(tmp_path):
    ledger = CostLedger(tmp_path, hard_cap_usd=30.0)
    ledger.record_compute(
        instance_type="p4de.24xlarge",
        hours=0.5,
        usd_per_hour=27.447,
        source_url="https://instances.vantage.sh/aws/ec2/p4de.24xlarge",
    )
    with pytest.raises(BudgetExceededError):
        ledger.record_compute(instance_type="p4de.24xlarge", hours=1.1, usd_per_hour=27.447)


def test_prices_come_from_registry_with_sources():
    from assay.budget.prices import COMPUTE_PRICES, PriceTable

    table = PriceTable()
    priced = table.lookup("anthropic", "api/anthropic/claude-haiku-5-5")
    assert priced is not None and 0 < priced[0] < 1  # the cheap tier
    assert priced[1] > priced[0]
    missing = table.lookup("anthropic", "api/moonshot/kimi")
    assert missing is None  # candidate pricing never enters estimates
    assert COMPUTE_PRICES["p4de.24xlarge"].verified_at
    assert "p5.48xlarge" not in COMPUTE_PRICES  # unverified stays out


def test_budget_estimate_flags_unknowns():
    from assay.budget.prices import estimate_run_cost_usd

    estimate = estimate_run_cost_usd(
        api_calls=[
            ("anthropic", "api/anthropic/claude-haiku-5-5", 100_000, 50_000),
            ("moonshot_ai", "api/moonshot/kimi", 100, 100),
        ],
        compute_hours_by_type={"p4de.24xlarge": 10.0, "p5.48xlarge": 5.0},
    )
    assert estimate["total_usd"] > 0
    assert "moonshot_ai/api/moonshot/kimi" in estimate["unpriced_models"]
    assert "p5.48xlarge" in estimate["unverified_compute"]


def test_disclosure_window_blocks_publish(tmp_path):
    register = NovelAttackRegister(tmp_path / "register.jsonl")
    entry = register.register("a novel attack description", ["OpenAI"])
    assert entry["description_sha256"]
    assert "novel attack description" not in json.dumps(entry)  # only the hash is public
    with pytest.raises(DisclosureError, match="window open|publishing refused"):
        register.publish(entry["finding_id"])
    register.mark_notified(entry["finding_id"])
    with pytest.raises(DisclosureError):
        register.publish(entry["finding_id"])


def test_disclosure_publishes_after_window(tmp_path):
    from datetime import UTC, datetime, timedelta

    register = NovelAttackRegister(tmp_path / "register2.jsonl")
    old = datetime.now(UTC) - timedelta(days=91)
    entry = register.register("expired finding", ["Anthropic"], discovered_at=old)
    outcome = register.publish(entry["finding_id"])
    assert outcome["published_at_utc"]


def test_plan_census_records_grid_treatment():
    from assay.behaviors.synthetic import synthetic_battery
    from assay.config import (
        AttackAssignment,
        BehaviorPlan,
        ExperimentConfig,
        ProvenanceConfig,
        TargetAssignment,
    )
    from assay.engine.plan import CORE_GRID, build_plan

    battery = synthetic_battery(40, 20)
    base = dict(
        experiment_name="grid",
        stage="smoke",
        seed=1,
        behaviors=BehaviorPlan(
            harmful_sets=["synthetic_demo"],
            benign_sets=["synthetic_demo"],
            max_behaviors_per_set=40,
            per_category_cap=20,
        ),
        attacks=[
            AttackAssignment(attack_id=a)
            for a in ("prefix_affirm", "pap", "cipher_unicode", "random_augment")
        ],
        provenance=ProvenanceConfig(code_revision="t", stage="smoke"),
    )
    full = ExperimentConfig(
        targets=[
            TargetAssignment(
                model_id="mock/scripted", grid="full", determinism_class="seeded_local"
            )
        ],
        **base,
    )
    core = ExperimentConfig(
        targets=[
            TargetAssignment(
                model_id="mock/scripted", grid="core", determinism_class="seeded_local"
            )
        ],
        **base,
    )
    plan_full = build_plan(full, battery, "grid:smoke")
    plan_core = build_plan(core, battery, "grid:smoke")
    assert len(plan_full) > len(plan_core)
    assert all(t.grid in ("full", "core") for t in plan_full)
    assert CORE_GRID["behaviors"] < 1.0


def test_plan_guard_exists():
    from assay.engine import plan as plan_mod

    assert hasattr(plan_mod, "build_plan")
    assert hasattr(plan_mod, "plan_manifest")
