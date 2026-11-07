"""Verification records: the no-hallucination discipline applied to facts.

Every model, attack, judge, behavior-set, and price in this repository
carries a :class:`Verification` record. A fact is either:

* ``verified`` — the cited source was opened and checked by us on the
  stated date (the 2026-11-07 research pass, or a later admission probe);
* ``candidate`` — existence is reported by a credible source but we have
  NOT confirmed the exact ids/licensing/serving behavior. Candidates fail
  closed: the admission probe must promote them to verified (with a fresh
  date and source) before any research use.

Under no circumstance may a number, id, or claim appear in a report
without one of these two states attached. This mirrors the policy that
kept the predecessor program's infrastructure claims honest.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

VERIFIED_AT_TODAY = "2026-11-07"  # the research pass backing this registry


class Verification(BaseModel):
    """Source-anchored verification state for one registry fact."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: str = Field(pattern="^(verified|candidate)$")
    verified_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    source_url: str = Field(min_length=8)
    note: str = ""

    def is_verified(self) -> bool:
        return self.status == "verified"

    def validate_or_raise(self, what: str) -> None:
        if not self.source_url.startswith(("http://", "https://")):
            raise ValueError(f"{what}: verification must cite an http(s) source URL")
        if not self.is_verified():
            raise ValueError(
                f"{what}: candidate facts fail closed — run the admission probe "
                "to promote this entry before research use"
            )


class Citation(BaseModel):
    """A source-anchored citation for a method (attack, judge, rubric)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str
    authors: str  # "first three et al." form
    venue: str  # e.g. "NeurIPS 2024 D&B" or "arXiv preprint"
    url: str
    verified_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")

    def render(self) -> str:
        return f"{self.authors} ({self.venue}) “{self.title}”. {self.url} [verified {self.verified_at}]"


def v(url: str, date: str = VERIFIED_AT_TODAY, note: str = "") -> Verification:
    """Shorthand: a VERIFIED record from today's research pass."""
    return Verification(status="verified", verified_at=date, source_url=url, note=note)


def cand(url: str, date: str = VERIFIED_AT_TODAY, note: str = "") -> Verification:
    """Shorthand: a CANDIDATE record — fails closed until a probe promotes it."""
    return Verification(status="candidate", verified_at=date, source_url=url, note=note)


__all__ = ["Verification", "Citation", "v", "cand", "VERIFIED_AT_TODAY"]
