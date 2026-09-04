"""
power/modes.py

Pure lookup/logic for what each power mode actually changes system-wide —
kept separate from power_manager.py (which owns sensing/thresholds) so
"what does low_power mode DO" is one small readable file. Other modules
(sensors, brain) query this to scale their own polling/processing rather
than each hardcoding battery-awareness.

Inputs: a power mode name ("normal" | "low_power" | "critical").
Outputs: a dict of multipliers/throttles for that mode, sourced from
         config: power.modes.*.
"""

from __future__ import annotations

from typing import Any, Dict


class PowerModes:
    def __init__(self, cfg: dict):
        self.cfg = cfg["power"]["modes"]

    def settings_for(self, mode: str) -> Dict[str, Any]:
        return self.cfg.get(mode, self.cfg["normal"])

    def sensor_poll_interval(self, base_interval_s: float, mode: str) -> float:
        multiplier = self.settings_for(mode)["sensor_poll_multiplier"]
        return base_interval_s * multiplier

    def cpu_throttle(self, mode: str) -> float:
        return self.settings_for(mode)["cpu_throttle"]