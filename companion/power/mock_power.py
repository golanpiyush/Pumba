"""
power/mock_power.py

Dev-machine stand-in for a real battery ADC. Simulates a slowly draining
battery (starting near full, decaying gradually) so power_manager.py has
something real to react to during development — mirrors sensors/
mock_sensors.py's role for sensing, and body/mock_display.py's role for
output.

Inputs: none (synthetic decay curve).
Outputs: a voltage value queried by power_manager.py in place of a real
         ADC read.
"""

from __future__ import annotations

import time


class MockBattery:
    def __init__(self, cfg: dict):
        self.cfg = cfg["power"]
        self._start_time = time.time()
        self._start_voltage = self.cfg["full_voltage"]
        # drains from full to empty over this many seconds, purely for
        # dev-mode visibility — tune freely, has no bearing on real hardware
        self._simulated_drain_duration_s = 1800.0

    def read_voltage(self) -> float:
        elapsed = time.time() - self._start_time
        drain_fraction = min(1.0, elapsed / self._simulated_drain_duration_s)
        voltage_range = self.cfg["full_voltage"] - self.cfg["empty_voltage"]
        return self.cfg["full_voltage"] - (voltage_range * drain_fraction)