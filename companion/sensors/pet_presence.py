"""
sensors/pet_presence.py

Fuses raw signals (PIR motion, ultrasonic echo-delta pattern, and later a
13MP camera) into a best-guess classification of WHICH animal is nearby:
bird, dog, or unknown. This is the module that lets the rest of the system
say "the bird did something" instead of just "something moved."

Heuristic today (no camera yet): a bird tends to produce small, fast,
high-frequency echo deltas and higher-pitched incidental sound; a dog
produces larger, slower echo deltas and lower-pitched sound/footsteps.
These thresholds live in config so they can be tuned per-household without
touching code.

Inputs: subscribes to sensor.motion, sensor.distance, and (future) an audio
        frequency-band summary event from voice/vad.py.
Outputs: Event(topic="pet.activity_detected") with payload {"animal":
         "bird"|"dog"|"unknown", "confidence": float, "signal": str}.
"""

from __future__ import annotations

import time
from collections import deque

from sensors.sensor_bus import SensorBus, Event


class PetPresenceDetector:
    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg["sensors"]["pet_presence"]
        self.bus = bus
        self._recent_distance_deltas: deque[float] = deque(maxlen=10)

    def start(self) -> None:
        self.bus.subscribe("sensor.distance", self._on_distance)
        self.bus.subscribe("sensor.motion", self._on_motion)
        # SENSOR INPUT HOOK: subscribe to a future "sensor.audio_band" event
        # once voice/vad.py exposes frequency-band summaries, and to a future
        # "sensor.camera_detection" event once the 13MP camera + a
        # lightweight vision classifier are added.

    def stop(self) -> None:
        pass

    def _on_distance(self, event: Event) -> None:
        distance_cm = event.payload.get("distance_cm")
        if distance_cm is None:
            return
        if self._recent_distance_deltas:
            delta = abs(distance_cm - self._recent_distance_deltas[-1])
            self._recent_distance_deltas.append(distance_cm)
            self._classify_from_echo_delta(delta)
        else:
            self._recent_distance_deltas.append(distance_cm)

    def _on_motion(self, event: Event) -> None:  # noqa: ARG002
        # Motion alone (no distance-delta history yet) is ambient — just a
        # weak "something is here" signal, handled by brain, not classified.
        pass

    def _classify_from_echo_delta(self, delta_cm: float) -> None:
        animal, confidence = self._guess_animal(delta_cm)
        if animal == "unknown":
            return
        self.bus.publish(Event(
            topic="pet.activity_detected",
            payload={"animal": animal, "confidence": confidence, "signal": "echo_delta"},
            urgency=0.3,
            source="pet_presence",
        ))

    def _guess_animal(self, delta_cm: float) -> tuple[str, float]:
        if delta_cm <= self.cfg["bird_max_echo_delta_cm"]:
            return "bird", self.cfg["bird_motion_confidence_min"]
        if delta_cm >= self.cfg["dog_min_echo_delta_cm"]:
            return "dog", self.cfg["dog_motion_confidence_min"]
        return "unknown", 0.0