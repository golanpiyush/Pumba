"""
brain/inspector/relevance_scorer.py

Scores how "worth remembering" a candidate episodic event is — this is the
judgment layer described in the design brief: most sensor noise should NOT
become a memory. Scores in [0, 1]; memory_manager.py compares against
config's memory.episodic.notability_score_min to decide long-vs-short
retention, and against inspector.relevance_min_score to decide whether to
store at all.

Signals considered (all heuristic/local — no LLM call needed for routine
scoring, keeping memory writes cheap and fast):
  - novelty: have we seen this near-exact event before recently?
  - emotional intensity: how far did mood move when this happened?
  - subject significance: events involving a known person/pet score higher
    than ambient environment noise.

Inputs: candidate event + current mood delta + recent history summary.
Outputs: float relevance score.
"""

from __future__ import annotations

from typing import Any, Dict

from sensors.sensor_bus import Event


class RelevanceScorer:
    def __init__(self, cfg: dict):
        self.cfg = cfg["brain"]["inspector"]

    def score(self, event: Event, mood_delta_magnitude: float, is_repeat_of_recent: bool) -> float:
        score = 0.0
        score += self._novelty_component(is_repeat_of_recent)
        score += self._emotional_component(mood_delta_magnitude)
        score += self._subject_component(event)
        return max(0.0, min(1.0, score))

    def _novelty_component(self, is_repeat_of_recent: bool) -> float:
        return 0.1 if is_repeat_of_recent else 0.4

    def _emotional_component(self, mood_delta_magnitude: float) -> float:
        return min(0.4, mood_delta_magnitude)

    def _subject_component(self, event: Event) -> float:
        if event.topic in {"pet.activity_detected", "voice.speaker_recognized", "sensor.fall_detected"}:
            return 0.3
        return 0.05

    def passes_storage_threshold(self, score: float) -> bool:
        return score >= self.cfg["relevance_min_score"]