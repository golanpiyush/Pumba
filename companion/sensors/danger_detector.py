"""
sensors/danger_detector.py

Fuses pet_presence.py's animal classification with proximity/sound cues to
decide when the bird (or dog) is plausibly IN DANGER right now, as opposed
to just "nearby" or "active." This is distinct from pet_presence.py itself
because presence detection answers "who is here" while this module answers
the much narrower, much more urgent question "is something bad about to
happen or already happening to them."

Two signal types feed in:
  - proximity danger: something (most often the dog, per config's
    danger_escalation.proximity_danger_cm_max) has gotten very close to the
    bird's position, closer than routine coexistence would predict.
  - distress sound: a sound event carrying dB and frequency information —
    SENSOR INPUT HOOK below is where a real microphone amplitude/frequency
    pipeline plugs in — that crosses the configured bird distress threshold
    rather than a routine chirp.

Both signal types must co-occur within danger_confirm_window_s to actually
fire pet.danger_detected — this guards against a coincidental loud noise OR
a coincidental close pass alone being mistaken for real danger, the same
way a real animal doesn't panic at a single ambiguous cue but does at two
correlated ones.

Inputs: subscribes to sensor.distance, pet.activity_detected, and a future
        sensor.sound_event (SENSOR INPUT HOOK — not yet produced by any
        module in this scaffold; wire in a microphone amplitude/FFT reader
        that publishes {"db": float, "freq_hz": float}).
Outputs: Event(topic="pet.danger_detected") / Event(topic="pet.danger_cleared").
"""

from __future__ import annotations

import time
from typing import Optional

from sensors.sensor_bus import SensorBus, Event


class DangerDetector:
    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg["danger_escalation"]
        self.bus = bus
        self._last_proximity_alert: Optional[float] = None
        self._last_distress_sound: Optional[float] = None
        self._danger_active = False

    def start(self) -> None:
        self.bus.subscribe("sensor.distance", self._on_distance)
        self.bus.subscribe("pet.activity_detected", self._on_activity)
        # SENSOR INPUT HOOK: subscribe to a future "sensor.sound_event" topic
        # once a real microphone amplitude/frequency pipeline exists; call
        # self._on_sound(event) with payload {"db": float, "freq_hz": float}.

    def stop(self) -> None:
        pass

    def _on_distance(self, event: Event) -> None:
        distance_cm = event.payload.get("distance_cm")
        if distance_cm is None:
            return
        if distance_cm <= self.cfg["proximity_danger_cm_max"]:
            self._last_proximity_alert = time.time()
            self._evaluate("bird")

    def _on_activity(self, event: Event) -> None:  # noqa: ARG002
        # Reserved: could use rapid, erratic bird activity as a soft signal
        # on its own in a future version. Currently only distance + sound
        # co-occurrence triggers danger, deliberately conservative to avoid
        # false alarms.
        pass

    def _on_sound(self, event: Event) -> None:
        db = event.payload.get("db", 0)
        freq_hz = event.payload.get("freq_hz", 0)
        if db >= self.cfg["bird_distress_sound_db_min"] and self._looks_like_distress_call(freq_hz):
            self._last_distress_sound = time.time()
            self._evaluate("bird")

    def _looks_like_distress_call(self, freq_hz: float) -> bool:
        # SENSOR INPUT HOOK: a real distress-call classifier (even a simple
        # frequency-band heuristic distinct from routine chirp range) goes
        # here. Placeholder always treats a qualifying dB level as distress.
        return True

    def _evaluate(self, animal: str) -> None:
        now = time.time()
        window = self.cfg["danger_confirm_window_s"]
        proximity_recent = self._last_proximity_alert and (now - self._last_proximity_alert) <= window
        sound_recent = self._last_distress_sound and (now - self._last_distress_sound) <= window

        if proximity_recent and sound_recent:
            self._danger_active = True
            self.bus.publish(Event(
                topic="pet.danger_detected",
                payload={"animal": animal, "is_trauma_tier": True},
                urgency=1.0,
                source="danger_detector",
            ))
        elif self._danger_active and not proximity_recent and not sound_recent:
            self._danger_active = False
            self.bus.publish(Event(
                topic="pet.danger_cleared",
                payload={"animal": animal},
                urgency=0.2,
                source="danger_detector",
            ))