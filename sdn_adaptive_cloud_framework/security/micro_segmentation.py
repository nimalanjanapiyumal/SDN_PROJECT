"""Micro-segmentation policy engine (Module 7)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Set, Tuple


@dataclass(frozen=True)
class SegmentRule:
    src_segment: str
    dst_segment: str
    allow: bool


class MicroSegmentationPolicy:
    """Default-deny policy with explicit allow rules.

    Default segments (configurable):
        web, app, db, admin, untrusted
    """

    DEFAULT_SEGMENTS = {"web", "app", "db", "admin", "untrusted"}

    def __init__(self, segments: Iterable[str] | None = None) -> None:
        self.segments: Set[str] = set(segments) if segments else set(self.DEFAULT_SEGMENTS)
        self._allow: Set[Tuple[str, str]] = set()

    def allow(self, src: str, dst: str) -> None:
        if src not in self.segments or dst not in self.segments:
            raise ValueError(f"unknown segment(s): {src}, {dst}")
        self._allow.add((src, dst))

    def deny(self, src: str, dst: str) -> None:
        self._allow.discard((src, dst))

    def is_allowed(self, src: str, dst: str) -> bool:
        return (src, dst) in self._allow

    def to_intents(self) -> List[Dict]:
        """Render the policy as a list of segmentation intents.

        Each pair of segments not present in ``self._allow`` is rendered as a
        ``segmentation/block`` intent; allowed pairs are rendered as
        ``segmentation/allow`` so they install at higher priority.
        """
        intents: List[Dict] = []
        for src in self.segments:
            for dst in self.segments:
                if src == dst:
                    continue
                action = "allow" if (src, dst) in self._allow else "block"
                intents.append({
                    "intent_type": "segmentation",
                    "action": action,
                    "src_segment": src,
                    "dst_segment": dst,
                    "priority": 90 if action == "allow" else 80,
                    "description": f"micro-seg {src} -> {dst}",
                })
        return intents


def default_policy() -> MicroSegmentationPolicy:
    """Build the policy described in the outline:

    web -> app, app -> db; untrusted is isolated.
    """
    p = MicroSegmentationPolicy()
    p.allow("web", "app")
    p.allow("app", "db")
    p.allow("admin", "web")
    p.allow("admin", "app")
    p.allow("admin", "db")
    return p


__all__ = ["SegmentRule", "MicroSegmentationPolicy", "default_policy"]
