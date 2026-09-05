"""
brain/entity_resolver.py

The "wait, what/who is that?" reasoning module. Every transcribed
utterance (from voice.transcript_ready) passes through here BEFORE going
to llm_router.py for general response generation, specifically to check:
does this sentence introduce, name, or reference an entity (bird/dog),
and if so, is that reference clear or ambiguous?

Three outcomes:
  1. CLEAR ACQUISITION — "I got a bird" / "I got a dog" with no name yet.
     Creates an entity stub immediately (memory/db_entities.py). This is
     always worth storing, regardless of relevance_scorer's usual
     threshold — see the inspector note below.
  2. CLEAR NAMING — "her name is Ken" / "I'll call him Ken" while exactly
     one unnamed stub of a plausible kind exists. Fills the name slot on
     the EXISTING stub rather than creating a new entity — this is the
     piece that makes "acquired 2 days before named" work correctly: the
     acquired_at timestamp is untouched, only named_at gets set now.
  3. AMBIGUOUS REFERENCE — a name-shaped word with no existing entity
     match and no unnamed stub to attach to ("I went with Ken" out of
     nowhere). This does NOT get stored as a fact. Instead it raises an
     Event(topic="brain.clarification_needed") which personality.py turns
     into an actual spoken question, and the ambiguity is filed in
     db_open_questions.py so it can be resolved (or re-asked) later.

This module is intentionally rule-based / pattern-based first — cheap
local heuristics — before ever needing an LLM call, consistent with the
system's "local rules before LLM" philosophy. Only genuinely difficult
phrasing falls through to the LLM router with a specific "resolve this
reference" framing.

Inputs: Event(topic="voice.transcript_ready").
Outputs: Event(topic="memory.entity_acquired"), Event(topic=
         "memory.entity_named"), Event(topic="brain.clarification_needed").
"""

from __future__ import annotations

import re
from typing import Optional

from sensors.sensor_bus import SensorBus, Event
from memory.db_entities import EntitiesDB
from memory.db_open_questions import OpenQuestionsDB

_ACQUISITION_PATTERNS = [
    (re.compile(r"\bi (?:got|brought home|adopted) (?:a|the) bird\b", re.I), "bird"),
    (re.compile(r"\bi (?:got|brought home|adopted) (?:a|the) dog\b", re.I), "dog"),
]

_NAMING_PATTERNS = [
    re.compile(r"\b(?:her|his|its|the bird'?s|the dog'?s) name is ([A-Z][a-zA-Z]+)\b"),
    re.compile(r"\bi(?:'ll| will)? (?:call|name) (?:her|him|it) ([A-Z][a-zA-Z]+)\b", re.I),
    re.compile(r"\bnamed (?:her|him|it) ([A-Z][a-zA-Z]+)\b", re.I),
]

# a bare capitalized word Pebble doesn't recognize, used in a way that
# implies it's a specific known entity ("with Ken", "Ken did X") — the
# ambiguity trigger
_UNRESOLVED_REFERENCE_PATTERN = re.compile(
    r"\b(?:with|and|told|saw|took|is|was) ([A-Z][a-zA-Z]{2,})\b"
)

# common words that look capitalized-and-name-shaped but aren't — kept
# small and explicit rather than a heavy NLP dependency
_COMMON_FALSE_POSITIVES = {"I", "The", "Pebble", "Monday", "Tuesday", "Wednesday",
                            "Thursday", "Friday", "Saturday", "Sunday", "Today", "Tomorrow"}


class EntityResolver:
    def __init__(self, cfg: dict, bus: SensorBus, entities_db: EntitiesDB, open_questions_db: OpenQuestionsDB):
        self.cfg = cfg["entity_resolver"]
        self.bus = bus
        self.entities = entities_db
        self.open_questions = open_questions_db

    def start(self) -> None:
        self.bus.subscribe("voice.transcript_ready", self._on_transcript)

    def stop(self) -> None:
        pass

        # add to EntityResolver._on_transcript, checked FIRST, before acquisition/naming:
    def _on_transcript(self, event: Event) -> None:
        text = event.payload.get("text", "")
        if not text:
            return

        if self._try_resolve_pending_question(text):
            return
        if self._try_handle_acquisition(text):
            return
        if self._try_handle_naming(text):
            return
        self._try_handle_ambiguous_reference(text)


    def _try_handle_acquisition(self, text: str) -> bool:
        for pattern, kind in _ACQUISITION_PATTERNS:
            if pattern.search(text):
                entity_id = self.entities.create_stub(kind=kind)
                self.bus.publish(Event(
                    topic="memory.entity_acquired",
                    payload={
                        "entity_id": entity_id, "kind": kind, "raw_text": text,
                        "is_notable": True,  # always worth remembering, per your request
                    },
                    urgency=0.4,
                    source="entity_resolver",
                ))
                return True
        return False

    def _try_handle_naming(self, text: str) -> bool:
        name = self._extract_name(text)
        if not name:
            return False

        # Try to find which unnamed stub this name most plausibly belongs
        # to. If there's exactly one candidate kind with an unnamed stub,
        # this is unambiguous. If there are multiple unnamed stubs across
        # kinds, or none at all, treat it as ambiguous instead of guessing.
        candidates = [
            stub for kind in ("bird", "dog")
            if (stub := self.entities.find_unnamed_stub(kind)) is not None
        ]

        if len(candidates) == 1:
            stub = candidates[0]
            self.entities.set_name(stub["id"], name)
            self.bus.publish(Event(
                topic="memory.entity_named",
                payload={
                    "entity_id": stub["id"], "kind": stub["kind"], "name": name,
                    "acquired_at": stub["acquired_at"], "raw_text": text,
                },
                urgency=0.4,
                source="entity_resolver",
            ))
            return True

        if len(candidates) == 0:
            # No unnamed stub exists at all — maybe this is renaming an
            # already-named entity, or introducing a name with no prior
            # "I got a ___" statement. Either way, ambiguous enough to ask
            # rather than silently create an orphaned fact.
            self._raise_ambiguous(name, text)
            return True

        # Multiple unnamed stubs (rare, but possible — e.g. got both pets
        # close together, neither named yet) — genuinely ambiguous.
        self._raise_ambiguous(name, text)
        return True

    def _extract_name(self, text: str) -> Optional[str]:
        for pattern in _NAMING_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(1)
        return None

    def _try_resolve_pending_question(self, text: str) -> bool:
            pending = self.open_questions.most_recent_open()
            if not pending:
                return False
            # simple confirmation pattern: "yes, that's the bird's name" /
            # "yes" / "it's the bird" — a real implementation would widen this,
            # but the key structural point is CHECKING for a pending question
            # before treating new input as an unrelated fresh statement.
            confirms_bird = re.search(r"\b(bird)\b", text, re.I) and re.search(r"\byes|yeah|yep\b", text, re.I)
            confirms_dog = re.search(r"\b(dog)\b", text, re.I) and re.search(r"\byes|yeah|yep\b", text, re.I)
            if not (confirms_bird or confirms_dog):
                return False
    
            kind = "bird" if confirms_bird else "dog"
            stub = self.entities.find_unnamed_stub(kind)
            if stub is None:
                return False
    
            self.entities.set_name(stub["id"], pending["candidate_referent"])
            self.open_questions.resolve(pending["id"], resolved_as=f"{kind}_name:entity_id={stub['id']}")
            self.bus.publish(Event(
                topic="memory.entity_named",
                payload={
                    "entity_id": stub["id"], "kind": kind, "name": pending["candidate_referent"],
                    "acquired_at": stub["acquired_at"], "raw_text": text,
                },
                urgency=0.4,
                source="entity_resolver",
            ))
            return True

    def _try_handle_ambiguous_reference(self, text: str) -> None:
        match = _UNRESOLVED_REFERENCE_PATTERN.search(text)
        if not match:
            return
        candidate = match.group(1)
        if candidate in _COMMON_FALSE_POSITIVES:
            return
        if self.entities.find_by_name(candidate) is not None:
            return  # already known — not actually ambiguous, nothing to do
        self._raise_ambiguous(candidate, text)

    def _raise_ambiguous(self, candidate_referent: str, source_utterance: str) -> None:
        self.open_questions.raise_question(candidate_referent, source_utterance)
        self.bus.publish(Event(
            topic="brain.clarification_needed",
            payload={"candidate_referent": candidate_referent, "source_utterance": source_utterance},
            urgency=0.5,
            source="entity_resolver",
        ))