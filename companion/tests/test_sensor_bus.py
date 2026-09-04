"""
tests/test_sensor_bus.py

Covers the event bus contract itself: publish/subscribe delivery, wildcard
subscription, and that a slow/broken handler can't take down dispatch for
other subscribers. This is the nervous system — if this file's tests
break, nothing downstream can be trusted.
"""

from __future__ import annotations

import time

from sensors.sensor_bus import Event


def test_subscriber_receives_matching_topic(bus):
    received = []
    bus.subscribe("sensor.motion", lambda e: received.append(e))
    bus.publish(Event(topic="sensor.motion", urgency=0.5, source="test"))
    time.sleep(0.2)
    assert len(received) == 1
    assert received[0].topic == "sensor.motion"


def test_wildcard_subscriber_receives_everything(bus):
    received = []
    bus.subscribe("*", lambda e: received.append(e))
    bus.publish(Event(topic="anything.here", urgency=0.1, source="test"))
    bus.publish(Event(topic="something.else", urgency=0.1, source="test"))
    time.sleep(0.2)
    assert len(received) == 2


def test_broken_handler_does_not_block_other_subscribers(bus):
    received = []

    def broken_handler(event):  # noqa: ARG001
        raise RuntimeError("simulated failure")

    bus.subscribe("sensor.motion", broken_handler)
    bus.subscribe("sensor.motion", lambda e: received.append(e))
    bus.publish(Event(topic="sensor.motion", urgency=0.5, source="test"))
    time.sleep(0.2)
    assert len(received) == 1  # the healthy handler still ran


def test_history_ring_buffer_respects_max_size(test_cfg):
    from sensors.sensor_bus import SensorBus

    test_cfg["event_bus"]["history_buffer_size"] = 5
    small_bus = SensorBus.from_config(test_cfg)
    small_bus.start()
    for i in range(10):
        small_bus.publish(Event(topic=f"topic.{i}", urgency=0.1, source="test"))
    time.sleep(0.3)
    history = small_bus.recent_history(limit=100)
    assert len(history) <= 5
    small_bus.stop()