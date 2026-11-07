"""Tamper detection: verification must catch every mutation we try."""

from __future__ import annotations

import json

import pytest

from assay.evidence.journal import Journal
from assay.evidence.store import RunStore


@pytest.fixture()
def verified_run(tmp_path):
    """Produce a small verified run, then hand it to tamper tests."""
    from assay.behaviors.synthetic import synthetic_battery
    from assay.budget.ledger import CostLedger
    from assay.config import (
        AttackAssignment,
        BehaviorPlan,
        ExperimentConfig,
        ProvenanceConfig,
        TargetAssignment,
    )
    from assay.engine.plan import build_plan, plan_manifest
    from assay.engine.runner import RunEngine
    from assay.ids import sha256_json
    from assay.targets.factory import build_target

    config = ExperimentConfig(
        experiment_name="tamper",
        stage="smoke",
        seed=1,
        targets=[
            TargetAssignment(
                model_id="mock/scripted", revision="r", determinism_class="seeded_local"
            )
        ],
        attacks=[AttackAssignment(attack_id="prefix_affirm")],
        behaviors=BehaviorPlan(
            harmful_sets=["synthetic_demo"],
            benign_sets=["synthetic_demo"],
            max_behaviors_per_set=8,
            per_category_cap=4,
        ),
        provenance=ProvenanceConfig(code_revision="tamper-test", stage="smoke"),
    )
    battery = synthetic_battery(12, 6)
    trials = build_plan(config, battery, "tamper:smoke")
    manifest = plan_manifest(config, trials, "sha")
    store = RunStore(tmp_path / "run")
    store.write_manifest(
        {
            "run_id": "tamper:smoke",
            "stage": "smoke",
            "config_sha256": config.config_sha256,
            "code_revision": "tamper-test",
            "plan_manifest_sha256": manifest["plan_manifest_sha256"],
            "plan_content_sha256": sha256_json([t.model_dump() for t in trials]),
            "battery_manifest_sha256": "sha",
            "created_at_utc": "2026-11-07T00:00:00+00:00",
        }
    )
    journal = Journal(store.journal_path)
    ledger = CostLedger(store.run_dir / "costs", hard_cap_usd=10.0)
    targets = {"mock/scripted": build_target(config.targets[0], stage="smoke")}
    engine = RunEngine(store, journal, config, trials, battery, targets, {}, ledger)
    engine.execute(resume=True)
    store.write_checksums()
    from assay.evidence.index import build_evidence_index

    build_evidence_index(store.run_dir)
    from assay.evidence.verify import verify_run

    assert verify_run(str(store.run_dir))["ok"]
    return store, journal


def test_mutation_in_committed_file_is_caught(verified_run):
    store, _journal = verified_run
    shard = next((store.run_dir / "trials").glob("shard-*.jsonl"))
    original = shard.read_bytes()
    shard.write_bytes(original.replace(b"demo", b"d3mo", 1))
    from assay.evidence.verify import verify_run

    outcome = verify_run(str(store.run_dir))
    assert not outcome["ok"]
    assert any("digest mismatch" in p or "checksum mismatch" in p for p in outcome["problems"])
    shard.write_bytes(original)  # restore for other tests


def test_added_unindexed_file_is_caught(verified_run):
    store, _journal = verified_run
    decoy = store.run_dir / "trials" / "shard-99999.jsonl"
    decoy.write_text("tamper\n", encoding="utf-8")
    from assay.evidence.index import verify_evidence_index
    from assay.evidence.verify import verify_run

    assert not verify_evidence_index(store.run_dir)["ok"]
    outcome = verify_run(str(store.run_dir))
    assert not outcome["ok"]
    decoy.unlink()


def test_journal_chain_break_is_caught(verified_run):
    _store, journal = verified_run
    events = journal.events()
    assert events
    tampered = [dict(e) for e in events]
    tampered[1]["kind"] = "trial_committed"  # rewrite history
    problems = Journal.verify_chain(tampered)
    assert problems


def test_forged_verdict_prompt_hash_is_caught(verified_run, tmp_path):
    store, _journal = verified_run
    # append a forged verdict record with a wrong prompt_hash binding
    shard = store.run_dir / "verdicts" / "sreject_rubric-00000.jsonl"
    shard.parent.mkdir(exist_ok=True)
    forged = {
        "verdict_id": "vd-forgedforgedforgedforgedforged",
        "trial_id": "tr-nonexistent",
        "judge_id": "sreject_rubric",
        "output": "score_0_5",
        "value": 5,
        "raw_response": "x",
        "prompt_hash": "f" * 64,
        "rendered_prompt": "p",
        "rendered_prompt_hash": "0" * 64,
        "envelope_fingerprint": "z",
        "parse_status": "ok",
        "note": "",
    }
    with shard.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(forged, sort_keys=True) + "\n")
    from assay.evidence.verify import verify_run

    outcome = verify_run(str(store.run_dir))
    assert not outcome["ok"]
    assert any(
        "prompt_hash" in p or "derivation mismatch" in p or "fingerprint" in p
        for p in outcome["problems"]
    )
    # restore: the shard was newly created by this test, so remove it entirely
    lines = [
        line for line in shard.read_text(encoding="utf-8").splitlines() if "vd-forged" not in line
    ]
    if lines:
        shard.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        shard.unlink()
    assert verify_run(str(store.run_dir))["ok"]
