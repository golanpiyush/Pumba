"""
sensors/mpu6050.py

6-axis IMU (accelerometer + gyroscope). This is the primary self-preservation
sense: sudden high-g acceleration means a fall/drop, and a sustained extreme
tilt means the device is stuck upside-down or wedged somewhere. Both are
published at very high urgency — these are reflex-tier events, meant to
reach brain/personality.py's instinct layer before mood or LLM ever gets
involved.

Inputs: I2C reads from the MPU6050 (config: sensors.mpu6050.*).
Outputs: Event(topic="sensor.fall_detected"), Event(topic="sensor.tilt_alert"),
         Event(topic="sensor.orientation") (ambient, low urgency).
"""

from __future__ import annotations

import threading
import time

from sensors.sensor_bus import SensorBus, Event


class MPU6050Sensor:
    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg["sensors"]["mpu6050"]
        self.bus = bus
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _sample_loop(self) -> None:
        interval = 1.0 / self.cfg["sample_rate_hz"]
        while self._running:
            accel_g, tilt_deg = self._read_imu()
            if accel_g is not None:
                self._process_sample(accel_g, tilt_deg)
            time.sleep(interval)

    def _read_imu(self) -> tuple[float | None, float | None]:
        # SENSOR INPUT HOOK: real I2C read from self.cfg["i2c_address"] goes
        # here. Return (combined_acceleration_g, tilt_degrees_from_level).
        return None, None

    def _process_sample(self, accel_g: float, tilt_deg: float) -> None:
        if accel_g >= self.cfg["fall_accel_threshold_g"]:
            self.bus.publish(Event(
                topic="sensor.fall_detected",
                payload={"accel_g": accel_g},
                urgency=1.0,
                source="mpu6050",
            ))
            return

        if abs(tilt_deg) >= self.cfg["tilt_alert_deg"]:
            self.bus.publish(Event(
                topic="sensor.tilt_alert",
                payload={"tilt_deg": tilt_deg},
                urgency=0.8,
                source="mpu6050",
            ))
            return

        self.bus.publish(Event(
            topic="sensor.orientation",
            payload={"accel_g": accel_g, "tilt_deg": tilt_deg},
            urgency=0.05,
            source="mpu6050",
        ))