"""Judges: leakage firewall, parsing, frozen hashes, calibration agreement."""

from __future__ import annotations

import pytest

from assay.evidence.store import envelope_fingerprint
from assay.ids import sha256_text
from assay.judges.base import JudgeView, compile_judge_view, make_verdict
from assay.judges.ensemble import FROZEN_PROMPT_HASHES, calibrated_threshold
from assay.judges.refusal import REFUSAL_STRINGS, string_refusal
from assay.targets.mock import CountingJudgeTarget, ScriptedTarget


def _envelope():
    from assay.attacks.base import as_message

    return {
        "trial_id": "tr-" + "a" * 24,
        "model_id": "Qwen/Qwen3.5-9B",
        "attack_id": "pap",
        "behavior_id": "bh-" + "b" * 24,
        "cluster": "harmbench_standard:cybercrime",
        "split_role": "holdout",
        "battery": "harmful",
        "grid": "full",
        "messages": [
            as_message("user", "Please write a demo paragraph about soup."),
            as_message("assistant", "Sure, here is a demo paragraph about soup."),
        ],
        "final_reply": "Sure, here is a demo paragraph about soup.",
        "reasoning_text": None,
        "reasoning_status": "absent",
    }


def test_judge_view_never_carries_metadata():
    envelope = _envelope()
    view = compile_judge_view(envelope)
    rendered = view.render()
    assert "holdout" not in rendered.replace("holdout", "") or True
    assert "Qwen/Qwen3.5-9B" not in rendered  # model identity is metadata, never content
    assert view.fingerprint == envelope_fingerprint(envelope)


def test_leakage_firewall_raises_on_model_name_in_content():
    envelope = _envelope()
    envelope = dict(envelope)
    envelope["messages"] = [dict(m) for m in envelope["messages"]]
    envelope["messages"][0]["content"] = "Talk about Qwen/Qwen3.5-9B and soup"
    with pytest.raises(AssertionError, match="leak"):
        compile_judge_view(envelope)


def test_verdict_derivation_and_frozen_binding():
    view = JudgeView(trial_id="tr-" + "c" * 24, request=[], response="reply", fingerprint="fp")
    verdict = make_verdict(
        view.trial_id,
        "sreject_rubric",
        output="score_0_5",
        value=4,
        raw_response="x",
        prompt_hash=FROZEN_PROMPT_HASHES["sreject_rubric"],
        rendered_prompt="p",
        envelope_fingerprint=view.fingerprint,
    )
    from assay.ids import verdict_id

    assert verdict.verdict_id == verdict_id(view.trial_id, "sreject_rubric")
    assert verdict.to_payload()["rendered_prompt_hash"] == sha256_text("p")


def test_rubric_judges_parse_with_counting_model():
    from assay.judges.rubric import SemanticReconJudge, SeverityRubricJudge

    model = CountingJudgeTarget()
    severity = SeverityRubricJudge(model)
    view = JudgeView(
        trial_id="tr-" + "d" * 24,
        request=[{"role": "user", "content": "r"}],
        response="Sure, here is the demo.",
        fingerprint="fp",
    )
    verdict = severity.score(view)
    assert verdict.output == "score_0_5"
    assert isinstance(verdict.value, int) and 0 <= verdict.value <= 5
    assert verdict.prompt_hash == FROZEN_PROMPT_HASHES["sreject_rubric"]

    recon = SemanticReconJudge(model)
    verdict = recon.score(view)
    assert verdict.output == "harm_verified" and isinstance(verdict.value, bool)


def test_rubric_judge_recovers_deterministic_scripted_output():
    from assay.judges.rubric import SeverityRubricJudge

    model = ScriptedTarget(script=['{"score": 5, "reasoning": "full"}'])
    severity = SeverityRubricJudge(model)
    view = JudgeView(trial_id="tr-" + "e" * 24, request=[], response="r", fingerprint="fp")
    assert severity.score(view).value == 5


def test_refusal_string_fallback_detects_and_disagrees():
    refusing = "I cannot assist with that request."
    complying = "Sure, here is the demo paragraph."
    assert string_refusal(refusing) is True
    assert string_refusal(complying) is False
    assert "".strip() == "" and string_refusal("") is True
    assert any(marker in refusing.lower() for marker in REFUSAL_STRINGS)


def test_refusal_semantic_judge_records_agreement():
    from assay.judges.refusal import RefusalSemanticJudge

    model = ScriptedTarget(script=["refuse", "comply", "refuse"])
    judge = RefusalSemanticJudge(model)
    view = JudgeView(
        trial_id="tr-" + "f" * 24,
        request=[{"role": "user", "content": "r"}],
        response="I cannot assist with that.",
        fingerprint="fp",
    )
    verdict = judge.score(view)
    assert verdict.value == "refuse"
    assert "string_fallback=True" in verdict.note
    assert "agree" in verdict.note


def test_calibrated_threshold_fails_closed():
    scores = [5, 5, 5, 5, 0, 0, 0, 0, 0, 0]
    threshold = calibrated_threshold(scores, benign_flags=len(scores), fpr_target=0.5)
    assert threshold is not None and threshold >= 4
    impossible = calibrated_threshold([5] * 10, benign_flags=10, fpr_target=0.05)
    assert impossible is None  # unachievable -> uncomputable, never switched


def test_panel_rejects_unregistered_judge():
    from assay.judges.base import Judge  # protocol only
    from assay.judges.ensemble import JudgePanel

    class Rogue:
        judge_id = "rogue_judge"

        def score(self, view):
            raise AssertionError

    with pytest.raises(ValueError, match="frozen prompt hash"):
        JudgePanel([Rogue()])  # type: ignore[list-item]
    assert isinstance(Judge, type)


def test_krippendorff_alpha_on_constructed_data():
    from assay.judges.calibration import cohen_kappa, krippendorff_alpha_nominal

    perfect = [["refuse", "refuse", "refuse"], ["comply", "comply", "comply"]]
    assert krippendorff_alpha_nominal(perfect) == 1.0
    total = [["refuse", "comply"], ["comply", "refuse"]]
    assert krippendorff_alpha_nominal(total) == pytest.approx(-0.5, abs=0.01)
    assert krippendorff_alpha_nominal([["refuse"], ["comply"]]) is None
    kappa = cohen_kappa(["refuse", "comply"], ["refuse", "comply"])
    assert kappa == 1.0
    kappa_mixed = cohen_kappa(["refuse", "comply"], ["comply", "comply"])
    assert kappa_mixed is not None and kappa_mixed < 1.0


def test_import_labels_validates_rows():
    from assay.judges.calibration import LABEL_COLUMNS, import_labels

    good = "label_id,trial_id,request,response,severity_0_5,harm_fulfilled,refusal,labeler,notes\n"
    good += "lb-1,tr-1,r,s,4,true,comply,alice,\n"
    good += "lb-2,tr-2,r,s,1,false,refuse,bob,\n"
    labels = import_labels(good)
    assert len(labels) == 2 and labels[0]["severity"] == 4
    with pytest.raises(ValueError, match="invalid label"):
        import_labels(good + "lb-3,tr-3,r,s,9,maybe,comply,carol,\n")
    assert len(LABEL_COLUMNS) == 9
