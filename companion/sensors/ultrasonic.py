"""
sensors/ultrasonic.py

HC-SR04-style ultrasonic distance sensor. Two jobs:
  1. Ambient distance sensing (used by pet_presence.py to help distinguish
     "small fast thing" bird movement from "big slow thing" dog movement,
     via echo-delta heuristics).
  2. Fall detection: a sudden jump in ground distance (the floor "appearing"
     farther away) is a strong physical signal the device has fallen or is
     tipping off an edge — published at high urgency so the instinct layer
     can react with zero LLM latency.

Inputs: trigger/echo GPIO pins (config: sensors.ultrasonic.*).
Outputs: Event(topic="sensor.distance"), Event(topic="sensor.possible_fall").
"""

from __future__ import annotations

import threading
import time
from collections import deque

from sensors.sensor_bus import SensorBus, Event


class UltrasonicSensor:
    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg["sensors"]["ultrasonic"]
        self.poll_interval = cfg["sensors"]["poll_interval_s"]
        self.bus = bus
        self._recent_readings: deque[float] = deque(maxlen=5)
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _poll_loop(self) -> None:
        while self._running:
            distance_cm = self._measure_distance_cm()
            if distance_cm is not None:
                self._process_reading(distance_cm)
            time.sleep(self.poll_interval)

    def _measure_distance_cm(self) -> float | None:
        # SENSOR INPUT HOOK: real trigger/echo pulse timing goes here using
        # self.cfg["trigger_pin"] / self.cfg["echo_pin"]. Return None on a
        # bad/out-of-range echo.
        return None

    def _process_reading(self, distance_cm: float) -> None:
        if distance_cm > self.cfg["max_valid_cm"]:
            return

        previous = self._recent_readings[-1] if self._recent_readings else distance_cm
        self._recent_readings.append(distance_cm)

        self.bus.publish(Event(
            topic="sensor.distance",
            payload={"distance_cm": distance_cm},
            urgency=0.1,
            source="ultrasonic",
        ))

        jump = distance_cm - previous
        if jump >= self.cfg["fall_drop_cm"]:
            self.bus.publish(Event(
                topic="sensor.possible_fall",
                payload={"distance_cm": distance_cm, "jump_cm": jump},
                urgency=0.95,
                source="ultrasonic",
            ))