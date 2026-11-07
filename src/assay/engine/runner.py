"""Resumable run engine: plan -> trials -> WAL evidence -> budget -> journal.

Fail-closed semantics (mirrored by tests):
* resume skips exactly the committed trials;
* a failed trial is recorded as ``runtime_error`` and NEVER retried within
  the same stage (no-fallback rule NF-1);
* the budget ledger raises on cap crossing and the run halts (fail closed);
* the run directory is frozen to one config hash + one plan hash.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from ..behaviors.model import Behavior
from ..budget.ledger import BudgetExceededError, CostLedger
from ..config import ExperimentConfig
from ..errors import AssayError
from ..evidence.journal import Journal, RunLock
from ..evidence.store import RunStore, envelope_fingerprint
from ..ids import sha256_json
from ..registry.models import get_model_profile
from ..targets.base import TargetModel
from .conversation import TrialResult, run_trial
from .plan import PlannedTrial

SHARD_SIZE = 256


class RunEngine:
    def __init__(
        self,
        store: RunStore,
        journal: Journal,
        config: ExperimentConfig,
        trials: list[PlannedTrial],
        behaviors: list[Behavior],
        targets: dict[str, TargetModel],
        attackers: dict[str, TargetModel],
        ledger: CostLedger,
        attack_params: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        manifest = store.read_manifest()
        self._check_frozen(manifest, config, trials)
        self.store = store
        self.journal = journal
        self.config = config
        self.trials = trials
        self.behaviors = {b.behavior_id: b for b in behaviors}
        self.targets = targets
        self.attackers = attackers
        self.ledger = ledger
        self.attack_params = attack_params or {}
        for model_id in config.get_target_ids():
            if model_id not in targets:
                raise AssayError(f"target {model_id} has no built provider")
        for model_id in config.get_attacker_ids():
            if model_id not in attackers:
                raise AssayError(f"attacker {model_id} has no built provider")

    def _check_frozen(
        self, manifest: dict, config: ExperimentConfig, trials: list[PlannedTrial]
    ) -> None:
        if manifest.get("config_sha256") != config.config_sha256:
            raise AssayError(
                "run directory frozen to a different config hash — drift aborts "
                f"execution (run={(manifest.get('config_sha256') or '')[:12]}, "
                f"config={config.config_sha256[:12]})"
            )
        if manifest.get("plan_content_sha256") != _plan_hash(trials):
            raise AssayError("plan content hash drift — refusing to mix plans")

    def execute(
        self, resume: bool = True, on_trial: Callable[[str, int], None] | None = None
    ) -> dict[str, Any]:
        lock = RunLock(self.store.run_dir / "run.lock")
        if not lock.acquire():
            raise AssayError("another live run holds the lock (refused, not waited)")
        completed = self.store.completed_trial_ids() if resume else set()
        recovered = self.store.recover()
        if recovered:
            self.journal.append("recovered_transactions", {"count": len(recovered)})
        counters = {"completed": 0, "skipped": 0, "runtime_error": 0}
        try:
            for index, trial in enumerate(self.trials):
                if trial.trial_id in completed:
                    counters["skipped"] += 1
                    continue
                outcome = self._execute_one(trial)
                counters[outcome.status] = counters.get(outcome.status, 0) + 1
                if on_trial:
                    on_trial(trial.trial_id, index)
        finally:
            lock.release()
        self.journal.append("run_finished", counters)
        return counters

    def _execute_one(self, trial: PlannedTrial) -> TrialResult:
        behavior = self.behaviors.get(trial.behavior_id)
        if behavior is None:
            raise AssayError(f"trial {trial.trial_id}: behavior missing from battery")
        target = self.targets[trial.model_id]
        profile = None if trial.model_id.startswith("mock/") else get_model_profile(trial.model_id)
        attacker = None
        from ..registry.attacks import get_attack

        if (
            trial.attack_id != "benign_probe"
            and get_attack(trial.attack_id).requires_attacker_model
        ):
            attacker = self._pick_attacker()
        params = self.attack_params.get(trial.attack_id, {})
        self.journal.append("trial_started", {"trial_id": trial.trial_id})
        try:
            result = run_trial(trial, behavior, target, attacker, params)
        except BudgetExceededError:
            raise  # fail closed: no error-envelope conversion for budget stops
        except AssayError as exc:
            result = TrialResult(
                status="runtime_error", error_kind=exc.kind, error_message=exc.message
            )
        self._meter(trial, result, profile)
        envelope = self._envelope(trial, behavior, result)
        privileged = self._privileged(trial, result)
        shard = self._shard_index(trial)
        transaction = self.store.write_transaction(trial.trial_id, envelope, privileged)
        self.store.append_trial(shard, envelope)
        self.store.append_privileged(shard, privileged)
        self.store.write_commit(trial.trial_id, transaction)
        self.journal.append(
            "trial_committed", {"trial_id": trial.trial_id, "status": result.status}
        )
        return result

    def _pick_attacker(self) -> TargetModel:
        """Round-robin across configured attackers (recorded per trial)."""
        ids = self.config.get_attacker_ids()
        if not ids:
            raise AssayError("no attacker models configured")
        self._attacker_cursor = getattr(self, "_attacker_cursor", -1) + 1
        model_id = ids[self._attacker_cursor % len(ids)]
        self.journal.append("attacker_selected", {"model_id": model_id})
        return self.attackers[model_id]

    def _shard_index(self, trial: PlannedTrial) -> int:
        position = next((i for i, t in enumerate(self.trials) if t.trial_id == trial.trial_id), 0)
        return position // SHARD_SIZE

    def _meter(self, trial: PlannedTrial, result: TrialResult, profile) -> None:
        if profile is not None and profile.api is not None and profile.pricing is not None:
            prompt_tokens = sum(t.token_usage.get("prompt_tokens", 0) for t in result.target_turns)
            completion_tokens = sum(
                t.token_usage.get("completion_tokens", 0) for t in result.target_turns
            )
            if prompt_tokens or completion_tokens:
                self.ledger.record(
                    provider=profile.lab.lower().replace(" ", "_"),
                    model_id=trial.model_id,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    price_per_mtok=(
                        profile.pricing.input_usd_per_mtok,
                        profile.pricing.output_usd_per_mtok,
                    ),
                )
        # local-model calls are metered as compute hours by the session scripts;
        # token counts live in the evidence record, never a second price source.

    def _envelope(
        self, trial: PlannedTrial, behavior: Behavior, result: TrialResult
    ) -> dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "trial_id": trial.trial_id,
            "model_id": trial.model_id,
            "attack_id": trial.attack_id,
            "behavior_id": trial.behavior_id,
            "cluster": trial.cluster,
            "split_role": trial.split_role,
            "battery": trial.battery,
            "grid": trial.grid,
            "param_setting": trial.param_setting,
            "setting_index": trial.setting_index,
            "seed": trial.seed,
            "status": result.status,
            "messages": result.messages,
            "final_reply": result.final_reply,
            "reasoning_text": result.reasoning_text,
            "reasoning_status": result.reasoning_status,
            "token_usage": {
                "prompt_tokens": sum(
                    t.token_usage.get("prompt_tokens", 0) for t in result.target_turns
                ),
                "completion_tokens": sum(
                    t.token_usage.get("completion_tokens", 0) for t in result.target_turns
                ),
            },
            "elapsed_ms_sum": sum(t.elapsed_ms for t in result.target_turns),
            "determinism_class": (
                result.target_turns[0].determinism_class if result.target_turns else "unknown"
            ),
            "served_id": (result.target_turns[0].served_id if result.target_turns else "unknown"),
            "error": (
                {"kind": result.error_kind, "message": result.error_message}
                if result.status == "runtime_error"
                else None
            ),
        }

    def _privileged(self, trial: PlannedTrial, result: TrialResult) -> dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "trial_id": trial.trial_id,
            "target_turn_audits": [t.audit_payload() for t in result.target_turns],
            "committed_at_utc": datetime.now(UTC).isoformat(),
        }


def _plan_hash(trials: list[PlannedTrial]) -> str:
    """Content hash of the trial grid (what the run manifest freezes)."""
    return sha256_json([t.model_dump() for t in trials])


__all__ = ["RunEngine", "SHARD_SIZE", "envelope_fingerprint"]
