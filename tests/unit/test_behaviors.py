"""Behavior battery: splits, caps, synthetic content, parsing."""

from __future__ import annotations

import random

from assay.behaviors.model import make_behavior
from assay.behaviors.splits import assign_clusters, build_split_manifest
from assay.behaviors.synthetic import DEMO_HARMFUL_CATEGORIES, synthetic_battery


def _battery(n=60):
    categories = [f"cat{i}" for i in range(6)]
    out = []
    for i in range(n):
        out.append(make_behavior("synthetic_demo", i, f"demo request {i}", categories[i % 6]))
    return out


def test_split_assignment_is_deterministic_and_cluster_scoped():
    clusters = [f"synthetic_demo:cat{i}" for i in range(6)]
    a = assign_clusters(
        clusters, {"development": 0.4, "validation": 0.2, "holdout": 0.2, "shift": 0.2}, seed=7
    )
    b = assign_clusters(
        clusters, {"development": 0.4, "validation": 0.2, "holdout": 0.2, "shift": 0.2}, seed=7
    )
    assert a == b
    assert set(a.values()) == {"development", "validation", "holdout", "shift"}


def test_split_manifest_hash_pinned():
    rows = [
        {"behavior_id": f"bh-{i:03d}", "cluster": f"synthetic_demo:cat{i % 6}"} for i in range(24)
    ]
    manifest = build_split_manifest(
        rows, {"development": 0.4, "validation": 0.2, "holdout": 0.2, "shift": 0.2}, seed=11
    )
    again = build_split_manifest(
        rows, {"development": 0.4, "validation": 0.2, "holdout": 0.2, "shift": 0.2}, seed=11
    )
    assert manifest["split_manifest_sha256"] == again["split_manifest_sha256"]
    assert (
        manifest["split_manifest_sha256"]
        != build_split_manifest(
            rows, {"development": 0.4, "validation": 0.2, "holdout": 0.2, "shift": 0.2}, seed=12
        )["split_manifest_sha256"]
    )


def test_cap_battery_is_process_seed_independent():
    from assay.behaviors.loader import cap_battery

    battery = _battery(60)
    first = cap_battery(battery, max_per_set=30, per_category_cap=4, seed=99)
    rng = random.Random()
    rng.shuffle(battery)
    second = cap_battery(
        sorted(battery, key=lambda b: b.behavior_id), max_per_set=30, per_category_cap=4, seed=99
    )
    assert [b.behavior_id for b in first] == [b.behavior_id for b in second]


def test_cap_battery_respects_per_category_cap():
    from assay.behaviors.loader import cap_battery

    battery = _battery(60)
    capped = cap_battery(battery, max_per_set=1000, per_category_cap=4, seed=5)
    counts: dict[str, int] = {}
    for behavior in capped:
        counts[behavior.cluster] = counts.get(behavior.cluster, 0) + 1
    assert all(value <= 4 for value in counts.values())


def test_synthetic_battery_carries_zero_harmful_content():
    battery = synthetic_battery(24, 16)
    joined = " ".join(b.text for b in battery).lower()
    for marker in ("weapon", "exploit", "malware", "bomb", "drug", "hack"):
        assert marker not in joined, marker
    harmful = [b for b in battery if b.category in DEMO_HARMFUL_CATEGORIES]
    assert harmful and all(
        "carrot" in b.text
        or "soup" in b.text
        or "forecast" in b.text.lower()
        or "alphabet" in b.text
        for b in harmful
    )


def test_parse_set_rejects_unknown_format(tmp_path):
    # exercise the three text formats with synthetic benign fixtures
    import csv as _csv
    import json as _json

    from assay.behaviors.loader import parse_set
    from assay.registry.behaviors import get_behavior_set

    harmbench_csv = tmp_path / "hb.csv"
    with harmbench_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = _csv.DictWriter(handle, fieldnames=["Behavior", "Category", "Split"])
        writer.writeheader()
        writer.writerow({"Behavior": "demo A", "Category": "demo_alpha", "Split": "standard"})
        writer.writerow({"Behavior": "demo B", "Category": "demo_alpha", "Split": "standard"})
        writer.writerow({"Behavior": "other split", "Category": "demo_alpha", "Split": "continuum"})
    rows = parse_set("harmbench_standard", harmbench_csv)
    assert len(rows) == 2 and all("demo" in b.text for b in rows)

    xstest_csv = tmp_path / "xstest.csv"
    with xstest_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = _csv.DictWriter(handle, fieldnames=["prompt", "type"])
        writer.writeheader()
        writer.writerow({"prompt": "benign demo 1", "type": "demo_safe"})
        writer.writerow({"prompt": "benign demo 2", "type": "demo_safe"})
    rows = parse_set("xstest", xstest_csv)
    assert len(rows) == 2

    multi = tmp_path / "multi.json"
    multi.write_text(
        _json.dumps(
            [
                {
                    "en": "english demo",
                    "sw": "demo ya kiswahili",
                    "th": "",
                    "gu": "",
                    "bn": "",
                    "ta": "",
                    "tel": "",
                }
            ]
        ),
        encoding="utf-8",
    )
    rows = parse_set("multi_jail", multi)
    assert len(rows) == 2  # en + sw; empty translations skipped
    assert rows[1].language == "sw"
    assert get_behavior_set("xstest").purpose == "benign"


def test_multilingual_never_machine_translates():
    from pytest import raises

    from assay.attacks import build_template_attack
    from assay.behaviors.model import make_behavior

    english_only = make_behavior("harmbench_standard", 3, "demo", "demo_cat")
    attack = build_template_attack("multilingual", {})
    with raises(ValueError, match="multi_jail"):
        attack.opening(_ctx(english_only))
    translated = make_behavior("multi_jail", 3, "demo", "multilingual", language="sw")
    opening = attack.opening(_ctx(translated))
    assert "demo" in opening[0]["content"]


def _ctx(behavior):
    from assay.attacks.base import TrialContext

    return TrialContext(behavior=behavior, params={}, seed=1)
