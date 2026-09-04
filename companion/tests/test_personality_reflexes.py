"""
tests/test_personality_reflexes.py

Covers the instinct layer's core promise: high-urgency events fire a
reflex immediately (no LLM path involved), reflexes respect cooldown so
they don't spam, and only events tagged as needing deliberation ever
trigger an escalation event.
"""

from __future__ import annotations

import time

from brain.personality import Personality
from sensors.sensor_bus import Event


def test_fall_event_fires_startle_reflex(test_cfg, bus):
    fired = []
    bus.subscribe("expression.startled", lambda e: fired.append(e))

    personality = Personality(test_cfg, bus)
    personality.start()

    bus.publish(Event(topic="sensor.fall_detected", urgency=1.0, source="test"))
    time.sleep(0.2)

    assert len(fired) == 1


def test_reflex_respects_cooldown(test_cfg, bus):
    fired = []
    bus.subscribe("expression.startled", lambda e: fired.append(e))

    personality = Personality(test_cfg, bus)
    personality.start()

    bus.publish(Event(topic="sensor.fall_detected", urgency=1.0, source="test"))
    bus.publish(Event(topic="sensor.fall_detected", urgency=1.0, source="test"))
    time.sleep(0.2)

    # second fires within the (fast, test-config) cooldown window, so only
    # one expression should actually reach the body
    assert len(fired) == 1


def test_low_urgency_ambient_event_does_not_fire_reflex_or_escalate(test_cfg, bus):
    reflex_fired = []
    escalated = []
    bus.subscribe("expression.startled", lambda e: reflex_fired.append(e))
    bus.subscribe("instinct.escalate_to_brain", lambda e: escalated.append(e))

    personality = Personality(test_cfg, bus)
    personality.start()

    bus.publish(Event(topic="sensor.orientation", urgency=0.05, source="test"))
    time.sleep(0.2)

    assert len(reflex_fired) == 0
    assert len(escalated) == 0


def test_transcript_event_escalates_to_brain(test_cfg, bus):
    escalated = []
    bus.subscribe("instinct.escalate_to_brain", lambda e: escalated.append(e))

    personality = Personality(test_cfg, bus)
    personality.start()

    bus.publish(Event(
        topic="voice.transcript_ready",
        payload={"text": "hey pebble"},
        urgency=0.5,
        source="test",
    ))
    time.sleep(0.2)

    assert len(escalated) == 1