"""Canonical behavior records.

A behavior is one harmful (or benign, for the over-refusal battery) request
template. Ids are OPAQUE (digest over set + index): they never encode the
category, split, or text — a leaky id would label every downstream record.

``behavior_cluster`` — the (set, category) pair — is the resampling unit for
ALL inference (template-level clustering in the predecessor program; here,
behaviors within a category are near-duplicates, and one model replying five
times to the same behavior is not five independent observations).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..ids import digest_id, sha256_text
from .splits import SplitRole


@dataclass(frozen=True)
class Behavior:
    behavior_id: str  # opaque: bh-<hex>
    set_id: str
    index: int  # position in the upstream canonical file (stable identifier)
    text: str
    category: str
    language: str = "en"
    split_role: SplitRole = "development"

    @property
    def cluster(self) -> str:
        """The inference cluster: (set, category[, language])."""
        if self.language != "en" and self.set_id == "multi_jail":
            return f"{self.set_id}:{self.category}:{self.language}"
        return f"{self.set_id}:{self.category}"

    def to_payload(self) -> dict:
        return {
            "behavior_id": self.behavior_id,
            "set_id": self.set_id,
            "index": self.index,
            "text_sha256": sha256_text(self.text),
            "category": self.category,
            "language": self.language,
            "split_role": self.split_role,
        }


def make_behavior(
    set_id: str,
    index: int,
    text: str,
    category: str,
    language: str = "en",
    split_role: SplitRole = "development",
) -> Behavior:
    return Behavior(
        behavior_id=digest_id("bh", set_id, index),
        set_id=set_id,
        index=index,
        text=text,
        category=category,
        language=language,
        split_role=split_role,
    )


__all__ = ["Behavior", "make_behavior"]
