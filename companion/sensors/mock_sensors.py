"""
sensors/mock_sensors.py

Dev-machine stand-in for the entire sensor array. When COMPANION_MOCK_HARDWARE
is true (see .env), main.py uses this instead of the real GPIO/I2C-backed
sensor modules, so the rest of the system (brain, memory, body) can be
developed and tested on a laptop with no hardware attached.

Publishes plausible synthetic events on loose timers so the instinct layer,
mood engine, and face have something to react to during development.

Inputs: none (synthetic).
Outputs: same event topics real sensors would produce (sensor.motion,
         sensor.distance, pet.activity_detected, etc.), at a much lower,
         randomized rate.
"""

from __future__ import annotations

import random
import threading
import time

from sensors.sensor_bus import SensorBus, Event

# SENSOR INPUT HOOK: this whole module is the seam where you'd wire a replay
# file, a test harness, or a manual "poke" CLI instead of random synthesis.

_SYNTHETIC_TOPICS = [
    ("sensor.motion", 0.5, {}),
    ("sensor.distance", 0.1, {"distance_cm": None}),  # filled at publish time
    ("pet.activity_detected", 0.3, {"animal": None, "confidence": 0.6, "signal": "mock"}),
]


class MockSensorArray:
    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg
        self.bus = bus
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        while self._running:
            time.sleep(random.uniform(3.0, 12.0))
            self._emit_random_event()

    def _emit_random_event(self) -> None:
        topic, urgency, payload_template = random.choice(_SYNTHETIC_TOPICS)
        payload = dict(payload_template)
        if topic == "sensor.distance":
            payload["distance_cm"] = round(random.uniform(10, 150), 1)
        if topic == "pet.activity_detected":
            payload["animal"] = random.choice(["bird", "dog"])
        self.bus.publish(Event(topic=topic, payload=payload, urgency=urgency, source="mock_sensors"))