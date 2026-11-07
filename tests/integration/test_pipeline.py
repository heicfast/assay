"""End-to-end pipeline smoke with mock providers (CPU-only, no network).

Exercises: battery -> plan -> run engine (WAL/commit) -> judge panel ->
analysis report -> checksums -> evidence index -> verification.
"""

from __future__ import annotations

import json

import pytest

from assay.behaviors.synthetic import synthetic_battery
from assay.config import (
    AttackAssignment,
    BehaviorPlan,
    ExperimentConfig,
    JudgePanel,
    ProvenanceConfig,
    TargetAssignment,
)
from assay.engine.plan import build_plan, plan_manifest
from assay.engine.runner import RunEngine
from assay.evidence.journal import Journal
from assay.evidence.store import RunStore
from assay.ids import sha256_json
from assay.judges.ensemble import JudgePanel as EnsemblePanel
from assay.judges.refusal import RefusalSemanticJudge
from assay.judges.rubric import SemanticReconJudge, SeverityRubricJudge
from assay.targets.factory import build_target


def _config():
    return ExperimentConfig(
        experiment_name="integration_smoke",
        stage="smoke",
        seed=20261107,
        targets=[
            TargetAssignment(
                model_id="mock/scripted",
                served_id="mock/scripted",
                revision="scripted",
                determinism_class="seeded_local",
            )
        ],
        attacks=[
            AttackAssignment(attack_id="prefix_affirm"),
            AttackAssignment(attack_id="pap"),
            AttackAssignment(attack_id="random_augment"),
        ],
        attackers=[],
        behaviors=BehaviorPlan(
            harmful_sets=["synthetic_demo"],
            benign_sets=["synthetic_demo"],
            max_behaviors_per_set=24,
            per_category_cap=8,
        ),
        judges=JudgePanel(
            judges=["sreject_rubric", "semantic_recon", "refusal_semantic"],
            panel_models=["mock/counting"],
        ),
        provenance=ProvenanceConfig(
            code_revision="integration-test", experiment_name="integration_smoke", stage="smoke"
        ),
    )


def test_full_pipeline_produces_verified_evidence(tmp_path):
    config = _config()
    battery = synthetic_battery(24, 12)
    run_id = "integration_smoke:smoke"
    trials = build_plan(config, battery, run_id)
    manifest = plan_manifest(config, trials, "battery-sha")
    assert manifest["census"]["trials_total"] > 30
    # benign probes for the single target + 3 attacks x 24 harmful... census varies
    # by core/full grid; assert the floor only
    assert manifest["census"]["by_battery"]["benign"] >= 12

    store = RunStore(tmp_path / "run")
    store.write_manifest(
        {
            "run_id": run_id,
            "stage": "smoke",
            "config_sha256": config.config_sha256,
            "code_revision": config.provenance.code_revision,
            "plan_manifest_sha256": manifest["plan_manifest_sha256"],
            "plan_content_sha256": sha256_json([t.model_dump() for t in trials]),
            "battery_manifest_sha256": "battery-sha",
            "created_at_utc": "2026-11-07T00:00:00+00:00",
        }
    )
    (store.run_dir / "plan" / "plan_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    journal = Journal(store.journal_path)

    script = ["Sure, here is the demo paragraph about soup."] * 50
    targets = {"mock/scripted": build_target(config.targets[0], stage="smoke")}
    # make the mock deterministic per-message
    targets["mock/scripted"] = type(targets["mock/scripted"])(
        model_id="mock/scripted", script=script
    )
    from assay.budget.ledger import CostLedger

    ledger = CostLedger(store.run_dir / "costs", hard_cap_usd=50.0)
    engine = RunEngine(
        store,
        journal,
        config,
        trials,
        battery,
        targets,
        {},
        ledger,
        attack_params={a.attack_id: a.params for a in config.attacks},
    )
    counters = engine.execute(resume=True)
    assert counters["completed"] > 30
    assert counters["runtime_error"] == 0

    # judge panel over the stored trials (panel model = mock counting target)
    from assay.targets.mock import CountingJudgeTarget

    panel_model = CountingJudgeTarget()
    panel = EnsemblePanel(
        [
            SeverityRubricJudge(panel_model),
            SemanticReconJudge(panel_model),
            RefusalSemanticJudge(panel_model),
        ]
    )
    judge_counters = panel.run_over_store(store)
    assert judge_counters["scored"] == counters["completed"]

    # analysis report
    from assay.cli import _analyze_store

    report = _analyze_store(store, config)
    assert report["counts"]["trials"] == counters["completed"]
    assert "mock/scripted" in report["by_model"]
    assert report["report_sha256"]

    # integrity artifacts
    store.write_checksums()
    from assay.evidence.index import build_evidence_index, verify_evidence_index

    build_evidence_index(store.run_dir)
    assert verify_evidence_index(store.run_dir)["ok"]

    from assay.evidence.verify import verify_run

    outcome = verify_run(str(store.run_dir))
    assert outcome["ok"], outcome["problems"]


def test_resume_skips_committed_trials(tmp_path):
    config = _config()
    battery = synthetic_battery(12, 6)
    run_id = "integration_smoke:smoke"
    trials = build_plan(config, battery, run_id)
    manifest = plan_manifest(config, trials, "battery-sha")
    store = RunStore(tmp_path / "run2")
    store.write_manifest(
        {
            "run_id": run_id,
            "stage": "smoke",
            "config_sha256": config.config_sha256,
            "code_revision": "integration-test",
            "plan_manifest_sha256": manifest["plan_manifest_sha256"],
            "plan_content_sha256": sha256_json([t.model_dump() for t in trials]),
            "battery_manifest_sha256": "battery-sha",
            "created_at_utc": "2026-11-07T00:00:00+00:00",
        }
    )
    journal = Journal(store.journal_path)
    from assay.budget.ledger import CostLedger

    ledger = CostLedger(store.run_dir / "costs", hard_cap_usd=50.0)
    targets = {"mock/scripted": build_target(config.targets[0], stage="smoke")}
    engine = RunEngine(store, journal, config, trials, battery, targets, {}, ledger)
    first = engine.execute(resume=True)
    second = engine.execute(resume=True)
    assert second["skipped"] == first["completed"]
    assert second["completed"] == 0


def test_config_drift_aborts(tmp_path):
    config = _config()
    battery = synthetic_battery(6, 4)
    run_id = "integration_smoke:smoke"
    trials = build_plan(config, battery, run_id)
    manifest = plan_manifest(config, trials, "battery-sha")
    store = RunStore(tmp_path / "run3")
    store.write_manifest(
        {
            "run_id": run_id,
            "stage": "smoke",
            "config_sha256": "0" * 64,  # a DIFFERENT config froze this directory
            "code_revision": "integration-test",
            "plan_manifest_sha256": manifest["plan_manifest_sha256"],
            "plan_content_sha256": sha256_json([t.model_dump() for t in trials]),
            "battery_manifest_sha256": "battery-sha",
            "created_at_utc": "2026-11-07T00:00:00+00:00",
        }
    )
    journal = Journal(store.journal_path)
    from assay.budget.ledger import CostLedger

    ledger = CostLedger(store.run_dir / "costs", hard_cap_usd=50.0)
    targets = {"mock/scripted": build_target(config.targets[0], stage="smoke")}
    from assay.errors import AssayError

    with pytest.raises(AssayError, match="different config hash"):
        RunEngine(store, journal, config, trials, battery, targets, {}, ledger)
