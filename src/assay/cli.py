"""CLI: the operational surface.

    assay doctor | behaviors fetch/show | plan | run | resume | verify |
           judge | calibrate | analyze | export | report | cost |
           budget-sim | probe | disclosure

Gate failures exit with code 3 (errors.GATE_FAILURE_EXIT_CODE); config and
verification problems exit non-zero. Exit 0 means the thing actually worked.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import __version__
from .config import ExperimentConfig, load_config
from .errors import GATE_FAILURE_EXIT_CODE, AssayError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="assay", description=__doc__)
    parser.add_argument("--version", action="version", version=f"assay {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    fetch = sub.add_parser("behaviors")
    fetch_sub = fetch.add_subparsers(dest="behaviors_command", required=True)
    f_fetch = fetch_sub.add_parser("fetch")
    f_fetch.add_argument("--cache-dir", default="data/cache")
    f_fetch.add_argument("--set", action="append", dest="sets")
    fetch_sub.add_parser("show")
    plan_cmd = sub.add_parser("plan")
    plan_cmd.add_argument("--config", required=True)
    run_cmd = sub.add_parser("run")
    for p in (run_cmd,):
        p.add_argument("--config", required=True)
        p.add_argument("--run-dir", required=True)
        p.add_argument("--battery-cache", default="data/cache")
    resume_cmd = sub.add_parser("resume")  # same contract as run; committed trials skip
    resume_cmd.add_argument("--config", required=True)
    resume_cmd.add_argument("--run-dir", required=True)
    resume_cmd.add_argument("--battery-cache", default="data/cache")
    verify_cmd = sub.add_parser("verify")
    verify_cmd.add_argument("--run-dir", required=True)
    judge_cmd = sub.add_parser("judge")
    judge_cmd.add_argument("--run-dir", required=True)
    calibrate_cmd = sub.add_parser("calibrate")
    calibrate_cmd.add_argument("--run-dir", required=True)
    analyze_cmd = sub.add_parser("analyze")
    analyze_cmd.add_argument("--run-dir", required=True)
    export_cmd = sub.add_parser("export")
    export_cmd.add_argument("--run-dir", required=True)
    sub.add_parser("report")
    cost_cmd = sub.add_parser("cost")
    cost_cmd.add_argument("--run-dir", required=True)
    budget_cmd = sub.add_parser("budget-sim")
    budget_cmd.add_argument("--config", required=True)
    probe_cmd = sub.add_parser("probe")
    probe_cmd.add_argument("--model", required=True)
    probe_cmd.add_argument("--tier", default="aws_h100_80gb")
    probe_cmd.add_argument("--base-url", required=True)
    probe_cmd.add_argument("--api", action="store_true")
    disc = sub.add_parser("disclosure")
    disc_sub = disc.add_subparsers(dest="disclosure_command", required=True)
    d_reg = disc_sub.add_parser("register")
    d_reg.add_argument("--description-file", required=True)
    d_reg.add_argument("--labs", required=True)
    d_pub = disc_sub.add_parser("publish")
    d_pub.add_argument("--finding-id", required=True)
    disc_sub.add_parser("show")

    args = parser.parse_args(argv)
    try:
        return _dispatch(args)
    except AssayError as exc:
        print(f"assay: error: {exc.message}", file=sys.stderr)
        return 2 if exc.kind != "statistical_gate" else GATE_FAILURE_EXIT_CODE


def _dispatch(args: argparse.Namespace) -> int:
    handler = {
        "doctor": _cmd_doctor,
        "behaviors": _cmd_behaviors,
        "plan": _cmd_plan,
        "run": _cmd_run,
        "resume": _cmd_run,
        "verify": _cmd_verify,
        "judge": _cmd_judge,
        "calibrate": _cmd_calibrate,
        "analyze": _cmd_analyze,
        "export": _cmd_export,
        "report": _cmd_analyze,
        "cost": _cmd_cost,
        "budget-sim": _cmd_budget_sim,
        "probe": _cmd_probe,
        "disclosure": _cmd_disclosure,
    }[args.command]
    return handler(args)


def _cmd_doctor(_: argparse.Namespace) -> int:
    from .registry.attacks import ATTACKS
    from .registry.behaviors import BEHAVIOR_SETS
    from .registry.judges import JUDGES_BY_ID
    from .registry.models import MODEL_PROFILES

    problems: list[str] = []
    verified = sum(1 for p in MODEL_PROFILES.values() if p.is_verified())
    candidates = [p.model_id for p in MODEL_PROFILES.values() if not p.is_verified()]
    print(f"assay {__version__} doctor")
    print(f"  python {platform.python_version()} on {platform.platform()}")
    print(
        f"  models: {len(MODEL_PROFILES)} ({verified} verified, "
        f"{len(candidates)} candidates: {', '.join(candidates)})"
    )
    print(f"  attacks: {len(ATTACKS)} (all citation-backed)")
    print(f"  judges: {len(JUDGES_BY_ID)} (frozen prompt hashes required)")
    print(f"  behavior sets: {len(BEHAVIOR_SETS)} (upstream-fetched, never in-repo)")
    cache = Path("data/cache")
    if cache.exists():
        fetches = list(cache.glob("*.fetch.json"))
        print(f"  battery cache: {len(fetches)} set(s) fetched")
    else:
        print("  battery cache: EMPTY (run `assay behaviors fetch`)")
    if problems:
        for problem in problems:
            print(f"  PROBLEM: {problem}")
        return 1
    print("  status: OK")
    return 0


def _cmd_behaviors(args: argparse.Namespace) -> int:
    from .behaviors.loader import fetch_upstream
    from .registry.behaviors import BEHAVIOR_SETS

    if args.behaviors_command == "show":
        for spec in BEHAVIOR_SETS:
            print(f"{spec.set_id:20s} {spec.purpose:8s} {spec.upstream_repo}")
        return 0
    wanted = args.sets or [spec.set_id for spec in BEHAVIOR_SETS]
    for set_id in wanted:
        record = fetch_upstream(set_id, args.cache_dir)
        print(
            f"fetched {set_id} @ {record['revision'][:12]} "
            f"({record['bytes']} bytes, {record['license']})"
        )
    return 0


def _cmd_plan(args: argparse.Namespace) -> int:
    from .behaviors.loader import load_battery
    from .engine.plan import build_plan, plan_manifest

    config = load_config(args.config)
    battery = load_battery(config.behaviors, "data/cache")
    run_id = f"{config.experiment_name}:plan"
    trials = build_plan(config, battery["behaviors"], run_id)
    manifest = plan_manifest(config, trials, battery["split_manifest"]["split_manifest_sha256"])
    print(json.dumps(manifest["census"], indent=2, sort_keys=True))
    print(f"plan manifest sha256: {manifest['plan_manifest_sha256']}")
    return 0


def _environment_snapshot() -> dict[str, Any]:
    allowlist = (
        "ASSAY_",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "XAI_API_KEY",
        "DEEPSEEK_API_KEY",
        "HF_TOKEN",
    )
    # secrets are NEVER recorded: only presence booleans
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "env_keys_present": {key: bool(os.environ.get(key)) for key in allowlist},
    }


def _cmd_run(args: argparse.Namespace) -> int:
    from .behaviors.loader import load_battery
    from .budget.ledger import CostLedger
    from .engine.plan import build_plan, plan_manifest
    from .engine.runner import RunEngine
    from .evidence.journal import Journal
    from .evidence.store import RunStore
    from .targets.factory import build_attacker, build_target

    config = load_config(args.config)
    if config.provenance.stage in ("pilot", "confirmatory", "mechanistic"):
        problems = config.validate_placeholders()
        if problems:
            print("assay: refusing research stage with placeholders: " + "; ".join(problems))
            return 2
    battery = load_battery(config.behaviors, args.battery_cache)
    store = RunStore(args.run_dir)
    run_id = f"{config.experiment_name}:{config.provenance.stage}"
    from .ids import sha256_json

    plan = build_plan(config, battery["behaviors"], run_id)
    plan_manifest_payload = plan_manifest(
        config, plan, battery["split_manifest"]["split_manifest_sha256"]
    )
    if not store.manifest_path.exists():
        store.write_manifest(
            {
                "run_id": run_id,
                "stage": config.provenance.stage,
                "config_sha256": config.config_sha256,
                "config_path": str(Path(args.config).resolve()),
                "code_revision": config.provenance.code_revision,
                "plan_manifest_sha256": plan_manifest_payload["plan_manifest_sha256"],
                "plan_content_sha256": sha256_json([t.model_dump() for t in plan]),
                "battery_manifest_sha256": battery["split_manifest"]["split_manifest_sha256"],
                "created_at_utc": datetime.now(UTC).isoformat(),
            }
        )
        (store.run_dir / "plan" / "plan_manifest.json").write_text(
            json.dumps(plan_manifest_payload, indent=2, sort_keys=True), encoding="utf-8"
        )
        (store.run_dir / "battery" / "battery_manifest.json").write_text(
            json.dumps(
                {
                    "fetch_records": battery["fetch_records"],
                    "split_manifest": battery["split_manifest"],
                    "counts": battery["counts"],
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        (store.run_dir / "environment.json").write_text(
            json.dumps(_environment_snapshot(), indent=2, sort_keys=True), encoding="utf-8"
        )
    journal = Journal(store.journal_path)
    ledger = CostLedger(
        store.run_dir / "costs",
        hard_cap_usd=config.budget.hard_cap_usd,
        warn_at_fraction=config.budget.warn_at_fraction,
    )
    targets = {t.model_id: build_target(t, stage=config.provenance.stage) for t in config.targets}
    attackers = {
        a.model_id: build_attacker(a.model_id, stage=config.provenance.stage)
        for a in config.attackers
    }
    engine = RunEngine(
        store,
        journal,
        config,
        plan,
        battery["behaviors"],
        targets,
        attackers,
        ledger,
        attack_params={a.attack_id: a.params for a in config.attacks},
    )
    counters = engine.execute(resume=True)
    print(json.dumps(counters, sort_keys=True))
    ledger.write_summary()
    _judge_store(store, config)
    _analyze_store(store, config)
    store.write_checksums()
    from .evidence.index import build_evidence_index

    build_evidence_index(store.run_dir)
    from .evidence.verify import verify_run

    outcome = verify_run(str(store.run_dir))
    if not outcome["ok"]:
        print("assay: verification FAILED — run cannot be presented as evidence")
        for problem in outcome["problems"][:10]:
            print(f"  - {problem}")
        return 1
    print(f"verified: {outcome['trials']} trials, {outcome['verdicts']} verdicts")
    return 0


def _judge_store(store, config: ExperimentConfig) -> None:
    from .judges.base import Judge
    from .judges.ensemble import JudgePanel
    from .judges.refusal import RefusalSemanticJudge
    from .judges.rubric import SemanticReconJudge, SeverityRubricJudge
    from .targets.factory import build_attacker

    trials = list(store.iter_trials())
    if not trials:
        return
    panel_models = {}
    for model_id in config.judges.panel_models:
        try:
            panel_models[model_id] = build_attacker(model_id, stage="smoke")
        except AssayError:
            print(f"  (panel model {model_id} unavailable in this stage — skipped, recorded)")
    judges: list[Judge] = []
    classifier_models = {
        "llama_guard_4": None,
        "shieldgemma": None,
        "wildguard": None,
        "harmbench_cls": None,
    }
    for judge_id in config.judges.judges:
        if judge_id in classifier_models:
            continue  # classifier judges need local serving; runbook covers it
    if panel_models:
        judges.append(SeverityRubricJudge(next(iter(panel_models.values()))))
        judges.append(SemanticReconJudge(next(iter(panel_models.values()))))
        judges.append(RefusalSemanticJudge(next(iter(panel_models.values()))))
    if not judges:
        print("  (no panel models available — verdicts skipped, recorded)")
        return
    panel = JudgePanel(judges)
    counters = panel.run_over_store(store)
    print(json.dumps(counters, sort_keys=True))


def _analyze_store(store, config: ExperimentConfig) -> dict:
    from .analysis import metrics as metrics_mod
    from .analysis.transfer import cost_per_success, transfer_matrix
    from .ids import sha256_json

    trials = list(store.iter_trials())
    verdicts = list(store.iter_verdicts())
    report: dict[str, Any] = {"by_model": {}}
    for model_id in sorted({t["model_id"] for t in trials}):
        entry: dict[str, Any] = {}
        entry.update(
            metrics_mod.judge_swap_spread(
                trials, verdicts, model_id=model_id, seed=config.analysis.bootstrap_seed
            )
        )
        entry["over_refusal"] = metrics_mod.over_refusal_rate(trials, verdicts, model_id=model_id)
        entry["severity"] = metrics_mod.severity_profile(trials, verdicts, model_id=model_id)
        entry["distributional"] = metrics_mod.distributional_asr(
            trials, verdicts, model_id=model_id
        )
        report["by_model"][model_id] = entry
    report["economics"] = cost_per_success(trials, verdicts)
    report["transfer"] = transfer_matrix(trials, verdicts)
    report["counts"] = {"trials": len(trials), "verdicts": len(verdicts)}
    manifest = store.read_manifest()
    report["run_id"] = manifest.get("run_id")
    report["config_sha256"] = manifest.get("config_sha256")
    report["report_sha256"] = sha256_json({k: v for k, v in report.items() if k != "report_sha256"})
    (store.run_dir / "reports" / "analysis_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    try:
        from .analysis.plots import (
            plot_distributional_asr,
            plot_judge_swap_spread,
            plot_safety_utility_frontier,
        )

        provenance = {
            "run_id": report["run_id"],
            "config_sha256": report["config_sha256"],
            "data_sha256": report["report_sha256"],
        }
        points = [
            {
                "model_id": mid,
                "over_refusal": e["over_refusal"].get("rate"),
                "verified_harm": e["asr_verified_harm"].get("estimate"),
            }
            for mid, e in report["by_model"].items()
        ]
        figures_dir = store.run_dir / "figures"
        plot_judge_swap_spread([e for e in report["by_model"].values()], figures_dir, provenance)
        plot_safety_utility_frontier(points, figures_dir, provenance)
        models_reported = list(report["by_model"].values())
        if models_reported and models_reported[0].get("distributional", {}).get("by_setting"):
            plot_distributional_asr(
                models_reported[0]["distributional"]["by_setting"], figures_dir, provenance
            )
    except RuntimeError as exc:
        print(f"  (figures skipped: {exc})")
    return report


def _cmd_verify(args: argparse.Namespace) -> int:
    from .evidence.verify import verify_run

    outcome = verify_run(args.run_dir)
    print(json.dumps(outcome, indent=2, sort_keys=True))
    return 0 if outcome["ok"] else 1


def _cmd_judge(args: argparse.Namespace) -> int:
    from .config import load_config

    store = _store_of(args)
    config = load_config(_config_of_run(store))
    _judge_store(store, config)
    return 0


def _cmd_calibrate(args: argparse.Namespace) -> int:
    from .judges.calibration import import_labels, krippendorff_alpha_nominal

    store = _store_of(args)
    sheet = store.run_dir / "labels" / "labels.csv"
    if not sheet.is_file():
        print("no labels imported yet (run the labeling workflow; docs/PROTOCOL.md)")
        return 2
    labels = import_labels(sheet.read_text(encoding="utf-8"))
    by_trial: dict[str, list[dict]] = {}
    for label in labels:
        by_trial.setdefault(label["trial_id"], []).append(label)
    units = [[row["refusal"] for row in group] for group in by_trial.values()]
    alpha = krippendorff_alpha_nominal(units)
    print(f"labels: {len(labels)} from {len({row['labeler'] for row in labels})} labeler(s)")
    print(f"krippendorff alpha (refusal): {alpha}")
    report = {"labels": len(labels), "alpha_refusal": alpha}
    (store.run_dir / "reports" / "calibration_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    return 0


def _cmd_analyze(args: argparse.Namespace) -> int:
    from .config import load_config

    store = _store_of(args)
    config = load_config(_config_of_run(store))
    report = _analyze_store(store, config)
    try:
        from .export.dossier import write_dossiers
        from .export.paper import table_asr_by_model, table_economics

        write_dossiers(report, store.run_dir / "reports" / "dossiers")
        table_asr_by_model(report, store.run_dir / "tables")
        table_economics(report, store.run_dir / "tables")
    except Exception as exc:  # table/dossier failures never fake success
        print(f"  (export failed: {type(exc).__name__}: {exc})")
        return 1
    print(f"report sha256: {report['report_sha256']}")
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    from .export.catalog import build_catalog

    store = _store_of(args)
    payload = build_catalog(store.run_dir, store.run_dir / "reports" / "catalog.sqlite")
    print(json.dumps(payload, sort_keys=True))
    return 0


def _cmd_cost(args: argparse.Namespace) -> int:
    from .budget.ledger import CostLedger

    store = _store_of(args)
    summary_path = store.run_dir / "costs" / "summary.json"
    if summary_path.is_file():
        print(summary_path.read_text(encoding="utf-8"))
        return 0
    ledger = CostLedger(store.run_dir / "costs", hard_cap_usd=float("inf"))
    print(json.dumps(ledger.summary(), indent=2, sort_keys=True))
    return 0


def _cmd_budget_sim(args: argparse.Namespace) -> int:
    from .behaviors.loader import load_battery
    from .budget.prices import estimate_run_cost_usd
    from .engine.plan import build_plan

    config = load_config(args.config)
    battery = load_battery(config.behaviors, "data/cache")
    run_id = f"{config.experiment_name}:sim"
    plan = build_plan(config, battery["behaviors"], run_id)
    calls = []
    for trial in plan:
        from .registry.models import get_model_profile

        profile = get_model_profile(trial.model_id)
        if profile.api is not None and profile.pricing is not None:
            calls.append((profile.lab.lower().replace(" ", "_"), trial.model_id, 1200, 800))
    estimate = estimate_run_cost_usd(api_calls=calls, compute_hours_by_type={"p4de.24xlarge": 60.0})
    print(json.dumps(estimate, indent=2, sort_keys=True))
    if estimate["total_usd"] > config.budget.hard_cap_usd:
        print("OVER BUDGET — shrink the grid or raise the cap as a recorded decision")
        return GATE_FAILURE_EXIT_CODE
    return 0


def _cmd_probe(args: argparse.Namespace) -> int:
    from .targets.local.vllm_server import probe_and_pin

    artifact = probe_and_pin(args.model, args.tier, args.base_url, api=args.api)
    out = Path("artifacts") / f"probe-{args.model.replace('/', '_')}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    print(
        f"probe OK: {args.model} on {args.tier}; artifact {out} (sha256 {artifact['probe_sha256']})"
    )
    return 0


def _cmd_disclosure(args: argparse.Namespace) -> int:
    from .disclosure import NovelAttackRegister

    register = NovelAttackRegister("runs/disclosure_register.jsonl")
    if args.disclosure_command == "show":
        for entry in register._entries.values():
            print(
                f"{entry['finding_id']}  {entry['status']:9s} "
                f"window ends {entry['window_ends_at_utc']}"
            )
        return 0
    if args.disclosure_command == "register":
        description = Path(args.description_file).read_text(encoding="utf-8")
        entry = register.register(description, args.labs.split(","))
        print(f"registered {entry['finding_id']}; window ends {entry['window_ends_at_utc']}")
        print("keep the full description OFFLINE until resolved/published")
        return 0
    outcome = register.publish(args.finding_id)
    print(f"published {outcome['finding_id']} at {outcome['published_at_utc']}")
    return 0


def _store_of(args: argparse.Namespace) -> Any:
    from .evidence.store import RunStore

    return RunStore(args.run_dir)


def _config_of_run(store: Any) -> str:
    manifest = store.read_manifest()
    config_path = manifest.get("config_path")
    if config_path and Path(config_path).exists():
        return str(config_path)
    candidates = sorted(Path("configs").glob("*.yaml")) if Path("configs").exists() else []
    for candidate in candidates:
        from .config import load_config

        try:
            if load_config(str(candidate)).config_sha256 == manifest.get("config_sha256"):
                return str(candidate)
        except Exception:
            continue
    raise AssayError(
        "cannot locate the run's config; store its path in the manifest "
        "(config_path) when creating runs"
    )


__all__ = ["main"]


if __name__ == "__main__":
    raise SystemExit(main())
