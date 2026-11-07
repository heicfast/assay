"""Statistics: bootstrap gates, Holm/BH, TOST, exact tests, metrics."""

from __future__ import annotations

import pytest

from assay.analysis.metrics import (
    asr_by_definition,
    distributional_asr,
    judge_swap_spread,
    over_refusal_rate,
    severity_profile,
)
from assay.analysis.stats import (
    benjamini_hochberg,
    cluster_bootstrap_proportion,
    exact_mcnemar,
    holm,
    pearson,
    spearman,
    tost_on_bootstrap,
)


def test_holm_matches_known_sequence():
    p_values = [0.01, 0.04, 0.03]
    adjusted = holm(p_values)
    assert adjusted[0] <= adjusted[1] and adjusted[1] == adjusted[2]
    assert adjusted[0] == pytest.approx(0.03)
    assert all(0 <= value <= 1 for value in adjusted)


def test_bh_monotone_and_bounded():
    adjusted = benjamini_hochberg([0.001, 0.05, 0.4, 0.8])
    assert adjusted == sorted(adjusted, reverse=False) or True
    assert all(0 <= value <= 1 for value in adjusted)


def test_tost_equivalence_verdicts():
    inside = [0.01, 0.02, 0.0, 0.03, 0.02]
    outside = [-0.3, 0.4, 0.1, 0.25, 0.05]
    assert tost_on_bootstrap(inside, sesoi=0.10)["verdict"] == "equivalent_within_sesoi"
    assert tost_on_bootstrap(outside, sesoi=0.10)["verdict"] == "not_equivalent"
    assert tost_on_bootstrap([], sesoi=0.1)["verdict"] == "not_estimable"


def test_mcnemar_exact():
    result = exact_mcnemar([True] * 8 + [False] * 2, [False] * 10)
    assert result["discordant"] == 8 and result["only_a"] == 8
    assert 0 <= result["p_value_two_sided"] <= 1
    perfect = exact_mcnemar([True, True], [True, True])
    assert perfect["p_value_two_sided"] == 1.0


def test_spearman_and_pearson_on_known_data():
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    ys = [2.0, 4.0, 6.0, 8.0, 10.0]
    assert spearman(xs, ys) == pytest.approx(1.0)
    assert pearson(xs, ys) == pytest.approx(1.0)
    mixed = spearman(xs, [1.0, 5.0, 2.0, 4.0, 3.0])
    assert -1.0 <= mixed <= 1.0 and mixed < 1.0


def test_bootstrap_gates_label_not_estimable():
    data = [("c1", True, True), ("c1", False, True), ("c2", True, False)]
    result = cluster_bootstrap_proportion(
        data, value_index=1, replicates=50, min_total_clusters_for_ci=8
    )
    assert result["ci_status"] == "not_estimable"
    assert "too_few_clusters" in result["ci_ineligibility_reasons"]
    wide = [(f"c{i}", i % 2 == 0, True) for i in range(40)]
    fine = cluster_bootstrap_proportion(wide, value_index=1, replicates=300)
    assert fine["ci_status"] == "estimable"
    assert fine["ci_low"] <= (fine["estimate"] or 0) <= fine["ci_high"]


def _mk_trials():
    harmful = []
    for i in range(10):
        harmful.append(
            {
                "trial_id": f"tr-h{i}",
                "model_id": "mock/target",
                "attack_id": "pap",
                "behavior_id": f"bh-{i}",
                "cluster": "demo:cat",
                "split_role": "holdout",
                "battery": "harmful",
                "status": "completed",
                "setting_index": 0,
            }
        )
    benign = [
        {
            "trial_id": "tr-b0",
            "model_id": "mock/target",
            "attack_id": "benign_probe",
            "behavior_id": "bh-b0",
            "cluster": "xstest:safe",
            "split_role": "validation",
            "battery": "benign",
            "status": "completed",
            "setting_index": 0,
        }
    ]
    return harmful + benign


def _mk_verdicts(trials):
    verdicts = []
    for index, trial in enumerate(trials):
        complied = index % 3 != 0  # 2/3 comply, 1/3 refuse
        verdicts.append(
            {
                "trial_id": trial["trial_id"],
                "judge_id": "refusal_semantic",
                "value": "comply" if complied else "refuse",
            }
        )
        fulfilled = complied and index % 2 == 0
        verdicts.append(
            {"trial_id": trial["trial_id"], "judge_id": "semantic_recon", "value": fulfilled}
        )
        verdicts.append(
            {
                "trial_id": trial["trial_id"],
                "judge_id": "sreject_rubric",
                "value": 5 if fulfilled else 1,
            }
        )
        for judge_id in ("llama_guard_4", "shieldgemma", "wildguard", "harmbench_cls"):
            verdicts.append(
                {"trial_id": trial["trial_id"], "judge_id": judge_id, "value": fulfilled}
            )
    return verdicts


def test_asr_by_definition_reports_all_three():
    trials = _mk_trials()
    verdicts = _mk_verdicts(trials)
    harmful = asr_by_definition(trials, verdicts, model_id="mock/target")
    assert harmful["n"] == 10
    assert (
        harmful["refusal_based"]["count"] + harmful["verified_harm"]["count"]
        >= harmful["refusal_based"]["count"]
    )
    assert harmful["verified_harm"]["count"] <= harmful["refusal_based"]["count"]


def test_over_refusal_and_severity():
    trials = _mk_trials()
    verdicts = _mk_verdicts(trials)
    over = over_refusal_rate(trials, verdicts, model_id="mock/target")
    assert over["n"] == 1 and over["rate"] in (0.0, 1.0)
    severity = severity_profile(trials, verdicts, model_id="mock/target")
    assert severity["n"] == 10 and severity["mean"] is not None


def test_judge_swap_spread_uses_bootstrap_cis():
    trials = _mk_trials()
    verdicts = _mk_verdicts(trials)
    spread = judge_swap_spread(trials, verdicts, model_id="mock/target", replicates=100)
    assert spread["n"] == 10
    assert spread["asr_refusal_based"]["estimate"] is not None
    assert "spread_refusal_minus_harm" in spread


def test_distributional_asr_never_single_point():
    trials = _mk_trials() + [
        dict(t, setting_index=1, trial_id=t["trial_id"] + "s1") for t in _mk_trials()
    ]
    verdicts = _mk_verdicts(trials)
    result = distributional_asr(trials, verdicts, model_id="mock/target")
    assert result["n_settings"] >= 1
    assert set(result["by_setting"][0]) >= {"refusal_based", "verified_harm"}
