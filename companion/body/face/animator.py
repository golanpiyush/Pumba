"""
body/face/animator.py

Drives facial expression on the OLED (via oled_driver.py). This is the
single place that decides "what does my face look like right now,"
listening to both fast reflex expression events (expression.startled,
expression.curious_glance, ...) and slower mood.changed events, and
blending them: a reflex expression plays as a brief overlay/interrupt on
top of whatever the current mood's idle animation is.

Sprites live in body/face/sprites/ (PNG/frame-sequence assets, not code).

Inputs: Event(topic="expression.*"), Event(topic="mood.changed"),
        Event(topic="mode.changed") (privacy mode overrides expression with
        a fixed indicator, per operating_mode.privacy.face_indicator_color
        semantics carried over to the face rather than just RGB).
Outputs: frame draws to oled_driver.py; no bus events (leaf consumer).
"""

from __future__ import annotations

import random
import threading
import time
from pathlib import Path

from sensors.sensor_bus import SensorBus, Event
from body.face.oled_driver import OLEDDriver


class FaceAnimator:
    SPRITES_DIR = Path(__file__).parent / "sprites"

    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg["body"]["face"]
        self.bus = bus
        self.driver = OLEDDriver(cfg)
        self._current_mood = "curious"
        self._overlay_expression: str | None = None
        self._overlay_until = 0.0
        self._privacy_active = False
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        self.driver.init()
        self.bus.subscribe("expression.*", self._on_expression)
        self.bus.subscribe("mood.changed", self._on_mood_changed)
        self.bus.subscribe("mode.changed", self._on_mode_changed)
        self._running = True
        self._thread = threading.Thread(target=self._render_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _on_expression(self, event: Event) -> None:
        self._overlay_expression = event.topic.split(".", 1)[1]
        self._overlay_until = time.time() + 1.5  # brief interrupt, not a mode switch

    def _on_mood_changed(self, event: Event) -> None:
        self._current_mood = event.payload["mood"]

    def _on_mode_changed(self, event: Event) -> None:
        self._privacy_active = event.payload.get("mode") == "privacy"

    def _render_loop(self) -> None:
        interval = 1.0 / self.cfg["animator"]["fps"]
        next_blink = self._schedule_next_blink()
        while self._running:
            now = time.time()
            if self._privacy_active:
                self.driver.draw_privacy_indicator()
            elif self._overlay_expression and now < self._overlay_until:
                self.driver.draw_sprite_sequence(self._sprite_path(self._overlay_expression))
            else:
                self._overlay_expression = None
                if now >= next_blink:
                    self.driver.draw_sprite_sequence(self._sprite_path("blink"))
                    next_blink = self._schedule_next_blink()
                else:
                    self.driver.draw_sprite_sequence(self._sprite_path(f"idle_{self._current_mood}"))
            time.sleep(interval)

    def _schedule_next_blink(self) -> float:
        lo, hi = self.cfg["animator"]["blink_interval_s_range"]
        return time.time() + random.uniform(lo, hi)

    def _sprite_path(self, name: str) -> Path:
        return self.SPRITES_DIR / name