"""
brain/mood_engine.py

Continuous mood as a point in (valence, arousal) space — the classic
affective-science model, kept deliberately simple. Every event nudges the
point; every tick, the point decays back toward a configured baseline
(config: mood.baseline_valence/arousal, mood.decay_half_life_s).

The continuous point is then discretized into a named mood ("curious",
"bored", "annoyed", "sleepy", "excited") using thresholds in config.yaml
(mood.states.*). Named mood drives: face/RGB color, prompt_builder.py's
choice of prompts/mood/<name>.md, and TTS tone.

Inputs: every Event via notify_event() (called by brain/personality.py).
Outputs: Event(topic="mood.changed") whenever the discretized mood label
         changes (not every tick — only on transitions, so subscribers
         like the face don't get spammed).
"""

from __future__ import annotations

import threading
import time

from sensors.sensor_bus import SensorBus, Event


class MoodEngine:
    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg["mood"]
        self.bus = bus
        self.valence = self.cfg["baseline_valence"]
        self.arousal = self.cfg["baseline_arousal"]
        self._current_label = self._discretize()
        self._thread: threading.Thread | None = None
        self._running = False
        self._lock = threading.Lock()

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._tick_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def notify_event(self, event: Event) -> None:
        """Called by personality.py for every event on the bus."""
        delta = self.cfg["event_deltas"].get(self._map_topic_to_delta_key(event))
        if delta is None:
            return
        with self._lock:
            self.valence = self._clamp(self.valence + delta["valence"])
            self.arousal = self._clamp(self.arousal + delta["arousal"])
            self._maybe_emit_transition()

    def _map_topic_to_delta_key(self, event: Event) -> str | None:
        # Small translation table from bus topics to the named deltas in
        # config.yaml's mood.event_deltas. Kept here (not in config) because
        # it's structural wiring, not a tunable number.
        mapping = {
            "pet.activity_detected": {
                "bird": "bird_activity",
                "dog": "dog_activity",
            }.get(event.payload.get("animal")),
            "voice.speaker_recognized": "person_recognized",
            "voice.stranger_detected": "stranger_detected",
            "sensor.fall_detected": "startle",
            "sensor.possible_fall": "startle",
            "feedback.praise": "praise",
            "feedback.scold": "scold",
        }
        return mapping.get(event.topic)

    def _tick_loop(self) -> None:
        interval = self.cfg["tick_interval_s"]
        while self._running:
            time.sleep(interval)
            self._decay_toward_baseline(interval)

    def _decay_toward_baseline(self, elapsed_s: float) -> None:
        half_life = self.cfg["decay_half_life_s"]
        decay_factor = 0.5 ** (elapsed_s / half_life)
        with self._lock:
            self.valence = self.cfg["baseline_valence"] + (self.valence - self.cfg["baseline_valence"]) * decay_factor
            self.arousal = self.cfg["baseline_arousal"] + (self.arousal - self.cfg["baseline_arousal"]) * decay_factor
            self._maybe_emit_transition()

    def _maybe_emit_transition(self) -> None:
        new_label = self._discretize()
        if new_label != self._current_label:
            self._current_label = new_label
            self.bus.publish(Event(
                topic="mood.changed",
                payload={"mood": new_label, "valence": self.valence, "arousal": self.arousal},
                urgency=0.1,
                source="mood_engine",
            ))

    def _discretize(self) -> str:
        s = self.cfg["states"]
        if self.arousal <= s["sleepy_arousal_max"]:
            return "sleepy"
        if self.arousal >= s["excited_arousal_min"]:
            return "excited"
        if self.valence <= s["annoyed_valence_max"] and self.arousal > s["bored_arousal_max"]:
            return "annoyed"
        if self.arousal <= s["bored_arousal_max"] and self.valence <= s["bored_valence_max"]:
            return "bored"
        if self.valence >= s["curious_valence_min"]:
            return "curious"
        return "curious"  # default resting state is curiosity, not neutrality

    @staticmethod
    def _clamp(x: float) -> float:
        return max(0.0, min(1.0, x))

    def current_mood(self) -> str:
        return self._current_label