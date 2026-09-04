"""
sensors/pir.py

PIR motion sensor. Publishes raw motion-detected events onto the bus.
Deliberately dumb: this module does not decide *what* moved (bird, dog,
person) — that interpretation happens downstream in pet_presence.py and
brain/personality.py. PIR just says "something moved, here, now."

Inputs: GPIO digital read from the PIR pin (config: sensors.pir.pin).
Outputs: Event(topic="sensor.motion") on the bus.
"""

from __future__ import annotations

import threading
import time

from sensors.sensor_bus import SensorBus, Event


class PIRSensor:
    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg["sensors"]["pir"]
        self.bus = bus
        self._last_trigger_time = 0.0
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _poll_loop(self) -> None:
        # SENSOR INPUT HOOK: replace _read_pin() with RPi.GPIO / gpiozero
        # digital input on self.cfg["pin"].
        poll_interval = 0.05
        while self._running:
            if self._read_pin():
                self._handle_trigger()
            time.sleep(poll_interval)

    def _read_pin(self) -> bool:
        # SENSOR INPUT HOOK: real GPIO read goes here. Returns True on motion.
        return False

    def _handle_trigger(self) -> None:
        now = time.time()
        if now - self._last_trigger_time < self.cfg["debounce_s"]:
            return
        self._last_trigger_time = now
        self.bus.publish(Event(
            topic="sensor.motion",
            payload={"pin": self.cfg["pin"]},
            urgency=0.5,
            source="pir",
        ))