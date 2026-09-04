#!/usr/bin/env python3
"""
main.py

Entry point. Boots every subsystem, wires them onto the shared SensorBus,
and starts the run loop. This file should stay thin — it is composition
root, not logic. If you're tempted to add behavior here, it probably
belongs in brain/personality.py (the instinct layer) instead.

Boot order matters:
  1. config + logging
  2. SensorBus (the nervous system everything else plugs into)
  3. power (so we know battery state before doing anything expensive)
  4. sensors (start sensing immediately)
  5. body (so it can express something the instant it boots — never a silent
     black screen)
  6. brain (personality/mood/instinct — the decision layer)
  7. memory (loaded after brain so brain can query it during boot greeting)
  8. voice, network (peripheral I/O, last)
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import signal
import sys
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv

from sensors.sensor_bus import SensorBus, Event


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def setup_logging(cfg: dict) -> None:
    log_cfg = cfg["logging"]
    Path(log_cfg["dir"]).mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        filename=Path(log_cfg["dir"]) / "companion.log",
        maxBytes=log_cfg["max_bytes"],
        backupCount=log_cfg["backup_count"],
    )
    logging.basicConfig(
        level=getattr(logging, log_cfg["level"]),
        handlers=[handler, logging.StreamHandler(sys.stdout)],
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


class Companion:
    """Owns the lifecycle of every subsystem. One instance per running pet."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.log = logging.getLogger("companion.main")
        self.bus = SensorBus.from_config(cfg)
        self._running = False
        # Subsystems are constructed lazily in boot() to keep import-time
        # side effects out of __init__, and so mock hardware substitution
        # (see COMPANION_MOCK_HARDWARE in .env) can be decided at boot time.
        self.power = None
        self.sensor_modules = []
        self.body = None
        self.brain = None
        self.memory = None
        self.voice = None
        self.network = None

    def boot(self) -> None:
        self.log.info("Booting %s...", self.cfg["identity"]["name"])

        # --- power -----------------------------------------------------
        from power.power_manager import PowerManager
        self.power = PowerManager(self.cfg, self.bus)
        self.power.start()

        # --- sensors -----------------------------------------------------
        use_mock = os.getenv("COMPANION_MOCK_HARDWARE", "true").lower() == "true"
        if use_mock:
            from sensors.mock_sensors import MockSensorArray
            self.sensor_modules = [MockSensorArray(self.cfg, self.bus)]
        else:
            from sensors.pir import PIRSensor
            from sensors.ultrasonic import UltrasonicSensor
            from sensors.mpu6050 import MPU6050Sensor
            from sensors.dpdt_mode_switch import ModeSwitch
            from sensors.pet_presence import PetPresenceDetector
            self.sensor_modules = [
                PIRSensor(self.cfg, self.bus),
                UltrasonicSensor(self.cfg, self.bus),
                MPU6050Sensor(self.cfg, self.bus),
                ModeSwitch(self.cfg, self.bus),
                PetPresenceDetector(self.cfg, self.bus),
            ]
        for module in self.sensor_modules:
            module.start()

        # --- body (express something immediately, even if just "booting") -
        from body.face.animator import FaceAnimator
        from body.rgb_visualizer import RGBVisualizer
        self.body = {
            "face": FaceAnimator(self.cfg, self.bus),
            "rgb": RGBVisualizer(self.cfg, self.bus),
        }
        for component in self.body.values():
            component.start()

        # --- brain (instinct layer + mood + LLM routing) ------------------
        from brain.personality import Personality
        self.brain = Personality(self.cfg, self.bus)
        self.brain.start()

        # --- memory --------------------------------------------------------
        from memory.memory_manager import MemoryManager
        self.memory = MemoryManager(self.cfg, self.bus)
        self.memory.start()

        # --- voice -----------------------------------------------------------
        from voice.vad import VoiceActivityDetector
        self.voice = VoiceActivityDetector(self.cfg, self.bus)
        self.voice.start()

        # --- network -----------------------------------------------------------
        from network.remote_bridge import RemoteBridge
        from network.connection_watchdog import ConnectionWatchdog
        self.network = {
            "bridge": RemoteBridge(self.cfg, self.bus),
            "watchdog": ConnectionWatchdog(self.cfg, self.bus),
        }
        for component in self.network.values():
            component.start()

        self.bus.publish(Event(topic="system.boot_complete", urgency=0.2, source="main"))
        self.log.info("Boot complete.")

    def run_forever(self) -> None:
        self._running = True
        self.bus.start()
        self.boot()
        signal.signal(signal.SIGINT, self._handle_shutdown_signal)
        signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
        while self._running:
            time.sleep(0.5)
        self.shutdown()

    def _handle_shutdown_signal(self, signum, frame) -> None:  # noqa: ARG002
        self.log.info("Shutdown signal received (%s).", signum)
        self._running = False

    def shutdown(self) -> None:
        self.log.info("Shutting down gracefully...")
        self.bus.publish(Event(topic="system.shutdown", urgency=0.4, source="main"))
        self.bus.stop()
        # SENSOR INPUT HOOK: real hardware modules should release GPIO/I2C
        # handles here (mock modules no-op).


def main() -> None:
    load_dotenv()
    cfg = load_config()
    setup_logging(cfg)
    companion = Companion(cfg)
    companion.run_forever()


if __name__ == "__main__":
    main()