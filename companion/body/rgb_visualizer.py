"""
body/rgb_visualizer.py

Drives an RGB LED strip/ring as a fast, glanceable mood indicator —
complementary to the face (which shows expression detail), this is meant
to be readable from across a room: color = mood, brightness pulse = arousal.

Also carries the privacy-mode indicator color (config: operating_mode.
privacy.face_indicator_color, mirrored here via body.rgb.colors.privacy)
so privacy status is visible even from an angle where the face isn't.

Inputs: Event(topic="mood.changed"), Event(topic="mode.changed").
Outputs: physical LED output; no bus events (leaf consumer).
"""

from __future__ import annotations

import threading
import time

from sensors.sensor_bus import SensorBus, Event


class RGBVisualizer:
    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg["body"]["rgb"]
        self.bus = bus
        self._current_mood = "curious"
        self._privacy_active = False
        self._strip = None

    def start(self) -> None:
        self._strip = self._init_strip()
        self.bus.subscribe("mood.changed", self._on_mood_changed)
        self.bus.subscribe("mode.changed", self._on_mode_changed)
        self._apply_color()

    def stop(self) -> None:
        pass

    def _init_strip(self):
        # SENSOR INPUT HOOK: real LED strip init (e.g. rpi_ws281x) on
        # self.cfg["pin"] with self.cfg["led_count"] goes here.
        return None

    def _on_mood_changed(self, event: Event) -> None:
        self._current_mood = event.payload["mood"]
        self._apply_color()

    def _on_mode_changed(self, event: Event) -> None:
        self._privacy_active = event.payload.get("mode") == "privacy"
        self._apply_color()

    def _apply_color(self) -> None:
        color_hex = self.cfg["colors"]["privacy"] if self._privacy_active else self.cfg["colors"].get(
            self._current_mood, self.cfg["colors"]["curious"]
        )
        self._set_strip_color(color_hex, self.cfg["brightness"])

    def _set_strip_color(self, color_hex: str, brightness: float) -> None:
        # SENSOR INPUT HOOK: real LED strip write goes here.
        pass