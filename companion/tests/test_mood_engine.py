"""
tests/test_mood_engine.py

Covers mood_engine.py's two core behaviors: events nudge valence/arousal
in the expected direction, and mood decays back toward baseline over time.
Also checks discretization thresholds produce the expected named mood at
a few known points, since prompt_builder.py and the face rely on that
label being correct.
"""

from __future__ import annotations

import time

from brain.mood_engine import MoodEngine
from sensors.sensor_bus import Event


def test_startle_event_drops_valence_and_raises_arousal(test_cfg, bus):
    mood = MoodEngine(test_cfg, bus)
    before_valence, before_arousal = mood.valence, mood.arousal
    mood.notify_event(Event(topic="sensor.fall_detected", urgency=1.0, source="test"))
    assert mood.valence < before_valence
    assert mood.arousal > before_arousal


def test_mood_decays_toward_baseline_over_time(test_cfg, bus):
    mood = MoodEngine(test_cfg, bus)
    mood.notify_event(Event(topic="sensor.fall_detected", urgency=1.0, source="test"))
    disturbed_arousal = mood.arousal
    mood.start()
    time.sleep(1.0)  # several tick_interval_s cycles given the fast test config
    mood.stop()
    assert abs(mood.arousal - test_cfg["mood"]["baseline_arousal"]) < abs(
        disturbed_arousal - test_cfg["mood"]["baseline_arousal"]
    )


def test_discretize_sleepy_at_low_arousal(test_cfg, bus):
    mood = MoodEngine(test_cfg, bus)
    mood.arousal = 0.05
    mood.valence = 0.5
    assert mood._discretize() == "sleepy"


def test_discretize_excited_at_high_arousal(test_cfg, bus):
    mood = MoodEngine(test_cfg, bus)
    mood.arousal = 0.9
    mood.valence = 0.6
    assert mood._discretize() == "excited"