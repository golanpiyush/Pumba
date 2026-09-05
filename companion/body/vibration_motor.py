"""
body/vibration_motor.py

Drives a small vibration motor (coin/ERM type) — a physical, unmistakable
"back off" signal distinct from sound, for close-range warnings (e.g. the
dog's nose is right at the cage). A brief buzz reads as an immediate
physical warning the way a real animal's sudden movement or puffed-up
posture would, faster and less escalatory than raising volume.

Pattern selection is driven by the same danger.escalation_stage events
amp_controller.py listens to, so sound and touch/vibration intensify
together — but vibration also fires on its own for very close-range
proximity alerts that haven't yet been confirmed as full "danger"
(pet_presence detecting the dog is a few cm away is a "get back" buzz
even before danger_detector.py's stricter co-occurrence check confirms
real danger).

Inputs: Event(topic="danger.escalation_stage"), Event(topic=
        "sensor.close_proximity_warning") (a lighter-weight, earlier
        signal than full danger detection).
Outputs: physical motor PWM output (SENSOR INPUT HOOK); no bus events.
"""

from __future__ import annotations

import threading
import time

from sensors.sensor_bus import SensorBus, Event


class VibrationMotor:
    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg["body"]["vibration"]
        self.bus = bus

    def start(self) -> None:
        self.bus.subscribe("danger.escalation_stage", self._on_escalation_stage)
        self.bus.subscribe("sensor.close_proximity_warning", self._on_proximity_warning)

    def stop(self) -> None:
        pass

    def _on_escalation_stage(self, event: Event) -> None:
        pattern = event.payload.get("pattern", "chirp_alert")
        self._buzz_pattern(self.cfg["patterns"].get(pattern, self.cfg["patterns"]["default"]))

    def _on_proximity_warning(self, event: Event) -> None:  # noqa: ARG002
        self._buzz_pattern(self.cfg["patterns"]["close_warning"])

    def _buzz_pattern(self, pattern: dict) -> None:
        thread = threading.Thread(target=self._run_pattern, args=(pattern,), daemon=True)
        thread.start()

    def _run_pattern(self, pattern: dict) -> None:
        for _ in range(pattern["pulses"]):
            self._set_motor_intensity(pattern["intensity"])
            time.sleep(pattern["pulse_on_s"])
            self._set_motor_intensity(0.0)
            time.sleep(pattern["pulse_off_s"])

    def _set_motor_intensity(self, intensity: float) -> None:
        # SENSOR INPUT HOOK: real PWM duty-cycle write to the motor driver
        # pin goes here, scaled by intensity in [0.0, 1.0].
        pass