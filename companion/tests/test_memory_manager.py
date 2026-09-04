"""
tests/test_memory_manager.py

Covers memory_manager.py's judgment pipeline: low-relevance ambient noise
should NOT be stored, while a notable event should be. Also covers that
plumbing events (system.*, instinct.reflex_fired, mood.changed) are never
treated as "experiences" worth storing at all.
"""

from __future__ import annotations

import time

from memory.memory_manager import MemoryManager
from sensors.sensor_bus import Event


def test_plumbing_events_are_never_storage_candidates(test_cfg, bus):
    mm = MemoryManager(test_cfg, bus)
    assert mm._is_storage_candidate(Event(topic="system.boot_complete")) is False
    assert mm._is_storage_candidate(Event(topic="instinct.reflex_fired")) is False
    assert mm._is_storage_candidate(Event(topic="mood.changed")) is False


def test_notable_event_gets_stored(test_cfg, bus):
    mm = MemoryManager(test_cfg, bus)
    mm.start()

    bus.publish(Event(
        topic="sensor.fall_detected",
        payload={"accel_g": 3.2},
        urgency=1.0,
        source="test",
    ))
    time.sleep(0.2)

    recent = mm.episodic.recent(limit=10)
    assert any(ep["topic"] == "sensor.fall_detected" for ep in recent)


def test_low_relevance_ambient_event_is_not_stored(test_cfg, bus):
    mm = MemoryManager(test_cfg, bus)
    mm.start()

    bus.publish(Event(
        topic="sensor.orientation",
        payload={"accel_g": 1.0, "tilt_deg": 2.0},
        urgency=0.05,
        source="test",
    ))
    time.sleep(0.2)

    recent = mm.episodic.recent(limit=10)
    assert not any(ep["topic"] == "sensor.orientation" for ep in recent)