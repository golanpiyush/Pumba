"""
power/power_manager.py

Monitors battery level and drives power-mode transitions (normal ->
low_power -> critical, defined in config: power.modes). This is a core part
of self-preservation: low/critical battery isn't just throttled silently —
it's published at high urgency so brain/personality.py's reflex table can
make the companion visibly/audibly ask for help before it dies, the way a
real animal signals distress rather than just quietly shutting down.

Inputs: periodic ADC read of battery voltage (config: power.
        battery_adc_channel).
Outputs: Event(topic="power.battery_level") (ambient, every poll),
         Event(topic="power.low_battery") / Event(topic="power.critical_battery")
         (high urgency, on threshold crossing only).
"""

from __future__ import annotations

import threading
import time

from sensors.sensor_bus import SensorBus, Event


class PowerManager:
    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg["power"]
        self.bus = bus
        self._current_mode = "normal"
        self._last_alerted_mode = "normal"
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
            voltage = self._read_battery_voltage()
            if voltage is not None:
                self._process_reading(voltage)
            time.sleep(self.cfg["poll_interval_s"])

    def _read_battery_voltage(self) -> float | None:
        # SENSOR INPUT HOOK: real ADC read on self.cfg["battery_adc_channel"]
        # goes here.
        return None

    def _process_reading(self, voltage: float) -> None:
        pct = self._voltage_to_percent(voltage)
        self.bus.publish(Event(
            topic="power.battery_level",
            payload={"percent": pct, "voltage": voltage},
            urgency=0.05,
            source="power_manager",
        ))
        self._update_mode_and_alert(pct)

    def _voltage_to_percent(self, voltage: float) -> int:
        full, empty = self.cfg["full_voltage"], self.cfg["empty_voltage"]
        pct = (voltage - empty) / (full - empty) * 100.0
        return max(0, min(100, round(pct)))

    def _update_mode_and_alert(self, pct: int) -> None:
        if pct <= self.cfg["critical_battery_pct"]:
            self._current_mode = "critical"
        elif pct <= self.cfg["low_battery_pct"]:
            self._current_mode = "low_power"
        else:
            self._current_mode = "normal"

        if self._current_mode != self._last_alerted_mode:
            self._last_alerted_mode = self._current_mode
            self._emit_alert_if_needed(pct)

    def _emit_alert_if_needed(self, pct: int) -> None:
        if self._current_mode == "critical":
            self.bus.publish(Event(
                topic="power.critical_battery",
                payload={"percent": pct},
                urgency=1.0,
                source="power_manager",
            ))
        elif self._current_mode == "low_power":
            self.bus.publish(Event(
                topic="power.low_battery",
                payload={"percent": pct},
                urgency=0.7,
                source="power_manager",
            ))

    def current_mode(self) -> str:
        return self._current_mode