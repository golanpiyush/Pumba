"""
sensors/environment_locator.py

Determines WHERE the device currently is — bird_cage, desk, or unknown —
by fusing available signals into a confidence-weighted guess, then
debouncing that guess over environment.location_confirm_window_s before
committing to a location change. This is what lets the rest of the system
(personality.py's priorities, commitment_watchdog.py's auto-fulfillment)
reason about "am I actually in the cage right now."

Today's signal (pre-camera): proximity pattern consistency. Being placed
in the bird cage produces a distinctive, stable close-range ultrasonic
reading (cage walls/perches nearby) combined with recurring bird-signature
motion — very different from being set on an open desk. This is a coarse
heuristic on purpose; a camera or a simple contact/reed switch on the cage
door would make this far more reliable later (see SENSOR INPUT HOOK).

Inputs: subscribes to sensor.distance, pet.activity_detected.
Outputs: Event(topic="environment.location_changed") only on debounced,
         confirmed transitions — never on every noisy reading.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Optional

from sensors.sensor_bus import SensorBus, Event


class EnvironmentLocator:
    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg["environment"]
        self.bus = bus
        self._recent_distances: deque[float] = deque(maxlen=20)
        self._recent_bird_signals: deque[float] = deque(maxlen=10)
        self._current_location = "unknown"
        self._pending_location: Optional[str] = None
        self._pending_since: Optional[float] = None

    def start(self) -> None:
        self.bus.subscribe("sensor.distance", self._on_distance)
        self.bus.subscribe("pet.activity_detected", self._on_pet_activity)
        # SENSOR INPUT HOOK: a physical reed/contact switch on the cage door,
        # or later a camera-based scene classifier, would replace this
        # entire heuristic with a much more reliable direct signal — wire
        # its event here instead of inferring from distance/motion patterns.

    def stop(self) -> None:
        pass

    def _on_distance(self, event: Event) -> None:
        distance_cm = event.payload.get("distance_cm")
        if distance_cm is not None:
            self._recent_distances.append(distance_cm)
        self._reevaluate()

    def _on_pet_activity(self, event: Event) -> None:
        if event.payload.get("animal") == "bird":
            self._recent_bird_signals.append(time.time())
        self._reevaluate()

    def _reevaluate(self) -> None:
        guess, confidence = self._guess_location()
        if confidence < self.cfg["location_confidence_min"]:
            return
        self._debounce_and_commit(guess)

    def _guess_location(self) -> tuple[str, float]:
        # Cage signature: consistently close ultrasonic readings AND recent
        # bird-signature motion within the last couple minutes.
        recent_bird_activity = any(
            (time.time() - t) < 120 for t in self._recent_bird_signals
        )
        if self._recent_distances:
            avg_distance = sum(self._recent_distances) / len(self._recent_distances)
            tightly_enclosed = avg_distance < 30  # cage walls are close, a desk's open air is not
            if tightly_enclosed and recent_bird_activity:
                return "bird_cage", 0.8
            if not tightly_enclosed:
                return "desk", 0.65
        return "unknown", 0.0

    def _debounce_and_commit(self, guess: str) -> None:
        now = time.time()
        if guess != self._pending_location:
            self._pending_location = guess
            self._pending_since = now
            return
        if (now - (self._pending_since or now)) < self.cfg["location_confirm_window_s"]:
            return  # not held long enough yet — could be noise
        if guess == self._current_location:
            return  # already here, nothing changed
        self._current_location = guess
        self.bus.publish(Event(
            topic="environment.location_changed",
            payload={"location": guess},
            urgency=0.2,
            source="environment_locator",
        ))