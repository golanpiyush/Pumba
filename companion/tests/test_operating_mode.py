"""
tests/test_operating_mode.py

Covers the safety-relevant invariant in operating_mode.py: a physical
privacy-switch assertion cannot be overridden by a software command, even
though software can freely switch between other modes when the physical
switch isn't asserting privacy.
"""

from __future__ import annotations

import time

from brain.operating_mode import OperatingMode
from sensors.sensor_bus import Event


def test_physical_switch_enters_privacy_mode(test_cfg, bus):
    changes = []
    bus.subscribe("mode.changed", lambda e: changes.append(e.payload["mode"]))

    mode = OperatingMode(test_cfg, bus)
    mode.start()

    bus.publish(Event(topic="sensor.mode_switch_changed", payload={"privacy_position": True}, source="test"))
    time.sleep(0.2)

    assert mode.is_privacy()
    assert "privacy" in changes


def test_software_cannot_override_physical_privacy_switch(test_cfg, bus):
    mode = OperatingMode(test_cfg, bus)
    mode.start()

    bus.publish(Event(topic="sensor.mode_switch_changed", payload={"privacy_position": True}, source="test"))
    time.sleep(0.2)
    assert mode.is_privacy()

    bus.publish(Event(topic="network.mode_command", payload={"mode": "normal"}, source="test"))
    time.sleep(0.2)

    assert mode.is_privacy()  # physical switch still wins


def test_software_can_switch_modes_when_physical_switch_is_off(test_cfg, bus):
    mode = OperatingMode(test_cfg, bus)
    mode.start()

    bus.publish(Event(topic="network.mode_command", payload={"mode": "debug"}, source="test"))
    time.sleep(0.2)

    assert mode.current_mode() == "debug"