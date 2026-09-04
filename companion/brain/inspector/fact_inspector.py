"""
brain/inspector/fact_inspector.py

Checks whether a candidate memory (an episodic event or a derived belief)
is actually a well-formed, checkable "fact" worth storing at all, before
memory_manager.py commits it. This is the first filter in the memory
pipeline — separate from relevance_scorer.py (is it worth REMEMBERING) and
contradiction_check.py (does it conflict with what we already believe).

Inputs: a candidate fact dict, e.g.
        {"subject": "bird", "predicate": "avoids", "object": "the red toy",
         "evidence_event_ids": [...]}.
Outputs: bool (is_well_formed) + optional cleanup of the fact dict.
"""

from __future__ import annotations

from typing import Any, Dict


class FactInspector:
    def __init__(self, cfg: dict):
        self.cfg = cfg

    def is_well_formed(self, candidate_fact: Dict[str, Any]) -> bool:
        required_keys = {"subject", "predicate", "object"}
        if not required_keys.issubset(candidate_fact.keys()):
            return False
        if not candidate_fact.get("evidence_event_ids"):
            return False  # no unsupported "facts" — everything traces to an event
        return True

    def normalize(self, candidate_fact: Dict[str, Any]) -> Dict[str, Any]:
        candidate_fact["subject"] = str(candidate_fact["subject"]).strip().lower()
        candidate_fact["predicate"] = str(candidate_fact["predicate"]).strip().lower()
        return candidate_fact