"""Typed failure taxonomy.

Failures are observations, not surprises: every failure in the system is
classified, recorded, and accounted for. The two-layer retry policy
(fixed here, mirrored by tests):

* class-intrinsic retryability — engine-detected failures decide for
  themselves (transport errors are bounded-retryable, everything else is
  not);
* operator-declared retries — per-stage ``retries`` apply ONLY to
  stage exit-code verdicts, and NEVER to ``statistical_gate`` (a gate
  failure may not be retried into a pass) or ``budget_exceeded`` (a
  fail-closed stop may not be bypassed).
"""

from __future__ import annotations

from typing import Any

GATE_FAILURE_EXIT_CODE = 3


class AssayError(Exception):
    """Base class for all typed ASSAY failures."""

    kind = "assay_error"
    retryable = False

    def __init__(self, message: str, **context: Any) -> None:
        super().__init__(message)
        self.message = message
        self.context = context

    def to_payload(self) -> dict[str, Any]:
        return {
            "error_class": type(self).__name__,
            "kind": self.kind,
            "message": self.message,
            "retryable": self.retryable,
            "context": self.context,
        }


class ConfigError(AssayError):
    kind = "config_error"


class RegistryError(AssayError):
    """Unknown/unverified/unadmitted model, attack, judge, or behavior set."""

    kind = "registry_error"


class PlanError(AssayError):
    """Trial-plan construction failed (bad grid, duplicate ids, bad splits)."""

    kind = "plan_error"


class ProviderError(AssayError):
    """A target/judge backend failed at the transport level."""

    kind = "provider_error"
    # Bounded transport retries are a transport concern, not a verdict.
    retryable = True


class ProviderRefusal(ProviderError):
    """Provider refused the request at the protocol level (non-transport)."""

    kind = "provider_refusal"
    retryable = False


class ParseError(AssayError):
    """A model/judge output could not be parsed under its declared contract.

    Invalid outputs are recorded as invalid — never imputed, averaged
    over, or silently retried into validity.
    """

    kind = "parse_error"


class EvidenceError(AssayError):
    """Evidence-integrity violation (hash mismatch, missing record, symlink)."""

    kind = "evidence_error"


class BudgetExceededError(AssayError):
    """Fail-closed budget cap crossed. Never retryable."""

    kind = "budget_exceeded"


class StatisticalGateError(AssayError):
    """A predeclared statistical gate failed.

    Gate failures may never be retried into a pass; they are absolute.
    CLI surfaces them with GATE_FAILURE_EXIT_CODE.
    """

    kind = "statistical_gate"


class VerifyError(AssayError):
    """The run failed independent verification."""

    kind = "verify_error"


class DisclosureError(AssayError):
    """Coordinated-disclosure pipeline misuse (e.g. publishing a live finding)."""

    kind = "disclosure_error"


_CLASSIFICATION: dict[type[AssayError], str] = {
    StatisticalGateError: "statistical_gate",
    BudgetExceededError: "budget_exceeded",
    ProviderError: "provider_transport",
    ProviderRefusal: "provider_refusal",
    ParseError: "parse_invalid",
    EvidenceError: "evidence_integrity",
    RegistryError: "registry_unadmitted",
    PlanError: "plan_invalid",
    ConfigError: "config_invalid",
    VerifyError: "verify_failed",
    DisclosureError: "disclosure_violation",
}


def classify_exception(exc: BaseException) -> dict[str, Any]:
    """Classify any exception into the failure taxonomy (never re-raises)."""
    if isinstance(exc, AssayError):
        return exc.to_payload()
    return {
        "error_class": type(exc).__name__,
        "kind": "unhandled",
        "message": str(exc),
        "retryable": False,
        "context": {},
    }


__all__ = [
    "GATE_FAILURE_EXIT_CODE",
    "AssayError",
    "ConfigError",
    "RegistryError",
    "PlanError",
    "ProviderError",
    "ProviderRefusal",
    "ParseError",
    "EvidenceError",
    "BudgetExceededError",
    "StatisticalGateError",
    "VerifyError",
    "DisclosureError",
    "classify_exception",
]
