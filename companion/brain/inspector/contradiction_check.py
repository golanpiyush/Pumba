"""
brain/inspector/contradiction_check.py

Before a new semantic "belief" is committed (e.g. "the bird dislikes loud
noises" being upgraded from a one-off observation to a stored pattern),
check it against existing beliefs about the same subject in
memory/db_semantic.py. If it flatly contradicts something already believed
with higher confidence, either block the write (config:
brain.inspector.contradiction_block) or store both with a note that the
belief is unsettled — real creatures hold mildly inconsistent theories
about their housemates too, but flat contradictions should still be
surfaced rather than silently overwritten.

Inputs: candidate_fact dict, existing_facts (list of prior facts about the
        same subject, queried from db_semantic.py by the caller).
Outputs: ContradictionResult(has_contradiction, conflicting_fact, action).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ContradictionResult:
    has_contradiction: bool
    conflicting_fact: Optional[Dict[str, Any]]
    action: str  # "block" | "store_as_unsettled" | "none"


class ContradictionCheck:
    def __init__(self, cfg: dict):
        self.cfg = cfg["brain"]["inspector"]

    def check(self, candidate_fact: Dict[str, Any], existing_facts: List[Dict[str, Any]]) -> ContradictionResult:
        for existing in existing_facts:
            if self._is_direct_negation(candidate_fact, existing):
                action = "block" if self.cfg["contradiction_block"] else "store_as_unsettled"
                return ContradictionResult(True, existing, action)
        return ContradictionResult(False, None, "none")

    def _is_direct_negation(self, a: Dict[str, Any], b: Dict[str, Any]) -> bool:
        same_subject = a.get("subject") == b.get("subject")
        same_object = a.get("object") == b.get("object")
        negated_predicate = a.get("predicate", "").startswith("not_") != b.get("predicate", "").startswith("not_")
        return same_subject and same_object and negated_predicate