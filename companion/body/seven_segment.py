"""
body/seven_segment.py

Small seven-segment display used for terse status/debug readouts (e.g.
battery %, a countdown, an error code) — the kind of glanceable diagnostic
info that doesn't belong on the expressive face. Only actively used in
debug mode (config: operating_mode.debug.show_internal_state_on_face)
and for a couple of specific alerts (low battery countdown, offline timer).

Inputs: Event(topic="power.battery_level"), Event(topic="mode.changed"),
        Event(topic="network.offline_duration").
Outputs: physical seven-segment output; no bus events (leaf consumer).
"""

from __future__ import annotations

from sensors.sensor_bus import SensorBus, Event
from body.mock_display import MockDisplay


class SevenSegmentDisplay:
    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg["body"]["seven_segment"]
        self.bus = bus
        self._debug_mode = False
        self._device = None

    def start(self) -> None:
        self._device = self._init_device()
        self.bus.subscribe("power.battery_level", self._on_battery_level)
        self.bus.subscribe("mode.changed", self._on_mode_changed)

    def stop(self) -> None:
        pass

    def _init_device(self):
        # SENSOR INPUT HOOK: real seven-segment I2C init (e.g. HT16K33) on
        # self.cfg["i2c_address"] goes here.
        return MockDisplay(width_px=4, height_px=1)

    def _on_mode_changed(self, event: Event) -> None:
        self._debug_mode = event.payload.get("mode") == "debug"

    def _on_battery_level(self, event: Event) -> None:
        if not self._debug_mode:
            return
        pct = event.payload.get("percent", 0)
        self._device.show_digits(f"{pct:>3d}%")