"""
body/face/oled_driver.py

Low-level OLED display driver (e.g. SSD1306 over I2C). This is the only
module that should import a hardware display library directly — everything
else (animator.py) talks in terms of sprite sequences, not pixels or I2C.

Inputs: sprite frame sequences / drawing commands from animator.py.
Outputs: physical pixels on the OLED.
"""

from __future__ import annotations

from pathlib import Path

from body.mock_display import MockDisplay


class OLEDDriver:
    def __init__(self, cfg: dict):
        self.cfg = cfg["body"]["face"]["oled"]
        self._device = None

    def init(self) -> None:
        # SENSOR INPUT HOOK: real display init (e.g. luma.oled SSD1306) on
        # self.cfg["i2c_address"] with dims (self.cfg["width_px"],
        # self.cfg["height_px"]) goes here. Falls back to MockDisplay so the
        # rest of the system runs identically without real hardware.
        self._device = MockDisplay(self.cfg["width_px"], self.cfg["height_px"])

    def draw_sprite_sequence(self, sprite_path: Path) -> None:
        if self._device is None:
            return
        # SENSOR INPUT HOOK: real frame-by-frame blit from sprite_path goes
        # here once sprite assets exist.
        self._device.show_placeholder(str(sprite_path))

    def draw_privacy_indicator(self) -> None:
        if self._device is None:
            return
        self._device.show_placeholder("privacy_indicator")