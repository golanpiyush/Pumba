"""
body/mock_display.py

Dev-machine stand-in for any physical display (OLED face, seven-segment).
Logs what WOULD have been drawn instead of touching real hardware, so
oled_driver.py and seven_segment.py behave identically whether or not
real hardware is attached (mirrors sensors/mock_sensors.py's role for
input).

Inputs: draw calls from oled_driver.py / seven_segment.py.
Outputs: log lines (no physical output).
"""

from __future__ import annotations

import logging

log = logging.getLogger("companion.mock_display")


class MockDisplay:
    def __init__(self, width_px: int, height_px: int):
        self.width_px = width_px
        self.height_px = height_px

    def show_placeholder(self, description: str) -> None:
        log.debug("MockDisplay(%dx%d) would show: %s", self.width_px, self.height_px, description)

    def show_digits(self, digits: str) -> None:
        log.debug("MockDisplay seven-segment would show: %s", digits)