"""
memory/memory_manager.py

Orchestrates the three memory stores (episodic, semantic, people) and owns
the judgment pipeline described in the design brief: not everything that
happens is worth remembering. Every event that reaches here has already
survived brain/personality.py's instinct filtering — this module decides
storage, not reaction.

Pipeline per candidate event:
  1. relevance_scorer.py scores it.
  2. If it clears inspector.relevance_min_score, store in episodic DB.
  3. Periodically (config: memory.consolidation.run_interval_s), run
     consolidation: look for repeated similar episodes
     (min_repeats_for_pattern) and promote them into semantic beliefs via
     fact_inspector.py + contradiction_check.py.

This is also where "growth over time" lives structurally: consolidation is
the mechanism by which isolated incidents become standing opinions.

Inputs: subscribes to '*' on SensorBus (post-instinct events worth
        considering for storage — ambient reflex-fired events are cheap to
        filter back out here too).
Outputs: writes to episodic/semantic/people DBs; publishes
         memory.pattern_detected when consolidation finds something new.
"""

from __future__ import annotations

import threading
import time
from collections import Counter
from typing import Any, Dict, List

from sensors.sensor_bus import SensorBus, Event
from memory.db_episodic import EpisodicDB
from memory.db_semantic import SemanticDB
from memory.db_people import PeopleDB
from brain.inspector.relevance_scorer import RelevanceScorer
from brain.inspector.fact_inspector import FactInspector
from brain.inspector.contradiction_check import ContradictionCheck
from brain.inspector.memory_worth_inspector import MemoryWorthInspector
from brain.time_awareness import TimeAwareness

class MemoryManager:
    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg
        self.bus = bus
        self.episodic = EpisodicDB(cfg)
        self.semantic = SemanticDB(cfg)
        self.people = PeopleDB(cfg)
        self.relevance_scorer = RelevanceScorer(cfg)
        self.fact_inspector = FactInspector(cfg)
        self.contradiction_check = ContradictionCheck(cfg)
        self.memory_worth = MemoryWorthInspector(cfg)
        self.time_awareness = TimeAwareness(cfg)
        self._consolidation_thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        self.episodic.connect()
        self.semantic.connect()
        self.people.connect()
        self.bus.subscribe("*", self._on_event)
        self._running = True
        self._consolidation_thread = threading.Thread(target=self._consolidation_loop, daemon=True)
        self._consolidation_thread.start()

    def stop(self) -> None:
        self._running = False

    def _on_event(self, event: Event) -> None:
        if not self._is_storage_candidate(event):
            return
        mood_valence_delta = event.payload.get("_mood_valence_delta", 0.0)
        mood_arousal_delta = event.payload.get("_mood_arousal_delta", 0.0)
        is_repeat = self._looks_like_recent_repeat(event)
        score = self.relevance_scorer.score(event, abs(mood_arousal_delta) or 0.2, is_repeat)
        if not self.relevance_scorer.passes_storage_threshold(score):
            return

        verdict = self.memory_worth.judge(
            topic=event.topic,
            payload=event.payload,
            relevance_score=score,
            mood_valence_delta=mood_valence_delta,
            mood_arousal_delta=mood_arousal_delta,
            time_context=self.time_awareness.context(),
        )

        tags = self._derive_tags(event) + [verdict.tier]
        self.episodic.insert_episode(
            topic=event.topic,
            payload={**event.payload, "recorded_on": self.time_awareness.today_str()},
            notability_score=score,
            tags=tags,
        )
        if verdict.is_permanent:
            self.bus.publish(Event(
                topic="memory.permanent_incident_logged",
                payload={"topic": event.topic, "reason": verdict.reason},
                urgency=0.2,
                source="memory_manager",
            ))

    def _is_storage_candidate(self, event: Event) -> bool:
        # Skip pure plumbing events — they're not "experiences."
        return not event.topic.startswith(("system.", "instinct.reflex_fired", "mood.changed"))

    def _looks_like_recent_repeat(self, event: Event) -> bool:
        recent = self.episodic.recent(limit=5)
        return any(r["topic"] == event.topic for r in recent)

    def _derive_tags(self, event: Event) -> List[str]:
        tags = [event.topic.split(".")[0]]
        if "animal" in event.payload:
            tags.append(event.payload["animal"])
        return tags

    def _consolidation_loop(self) -> None:
        interval = self.cfg["memory"]["consolidation"]["run_interval_s"]
        while self._running:
            time.sleep(interval)
            self._run_consolidation_pass()

    def _run_consolidation_pass(self) -> None:
        min_repeats = self.cfg["memory"]["consolidation"]["min_repeats_for_pattern"]
        recent = self.episodic.recent(limit=200)
        grouped = self._group_by_pattern_key(recent)
        for pattern_key, episodes in grouped.items():
            if len(episodes) < min_repeats:
                continue
            self._promote_to_belief(pattern_key, episodes)

    def _group_by_pattern_key(self, episodes: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for ep in episodes:
            animal = ep["payload"].get("animal")
            if not animal:
                continue
            key = f"{animal}:{ep['topic']}"
            groups.setdefault(key, []).append(ep)
        return groups

    def _promote_to_belief(self, pattern_key: str, episodes: List[Dict[str, Any]]) -> None:
        animal, topic = pattern_key.split(":", 1)
        candidate_fact = {
            "subject": animal,
            "predicate": "frequently_triggers",
            "object": topic,
            "evidence_event_ids": [e["id"] for e in episodes],
        }
        if not self.fact_inspector.is_well_formed(candidate_fact):
            return
        candidate_fact = self.fact_inspector.normalize(candidate_fact)

        existing = self.semantic.facts_about(animal)
        result = self.contradiction_check.check(candidate_fact, existing)
        if result.has_contradiction and result.action == "block":
            return

        confidence = min(0.95, 0.3 + 0.1 * len(episodes))
        self.semantic.upsert_fact(animal, candidate_fact["predicate"], candidate_fact["object"], confidence)
        self.bus.publish(Event(
            topic="memory.pattern_detected",
            payload={"subject": animal, "pattern": candidate_fact["object"], "confidence": confidence},
            urgency=0.1,
            source="memory_manager",
        ))