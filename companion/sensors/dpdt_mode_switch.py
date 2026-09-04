"""
sensors/dpdt_mode_switch.py

Physical DPDT toggle switch — a hardware-level, unmissable way to flip
operating mode (e.g. into privacy mode) without trusting software alone.
This matters for a device that listens/watches in a home: privacy mode
should be settable by a physical action even if the software stack is
misbehaving.

Inputs: GPIO digital read of switch position (config: sensors.dpdt_mode_switch.pin).
Outputs: Event(topic="sensor.mode_switch_changed") consumed by
         brain/operating_mode.py.
"""

from __future__ import annotations

import threading
import time

from sensors.sensor_bus import SensorBus, Event


class ModeSwitch:
    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg["sensors"]["dpdt_mode_switch"]
        self.bus = bus
        self._last_state: bool | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _poll_loop(self) -> None:
        poll_interval = 0.2
        while self._running:
            state = self._read_switch()
            if state != self._last_state:
                self._last_state = state
                self._emit_change(state)
            time.sleep(poll_interval)

    def _read_switch(self) -> bool:
        # SENSOR INPUT HOOK: real GPIO read on self.cfg["pin"] goes here.
        # True = privacy position, False = normal position.
        return False

    def _emit_change(self, privacy_position: bool) -> None:
        self.bus.publish(Event(
            topic="sensor.mode_switch_changed",
            payload={"privacy_position": privacy_position},
            urgency=0.6,
            source="dpdt_mode_switch",
        ))