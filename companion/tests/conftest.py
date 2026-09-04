"""
tests/conftest.py

Shared pytest fixtures for the test suite. Provides a minimal in-memory
config dict (mirroring config.yaml's shape, but with tiny/fast values so
tests don't sleep for real timeouts) and a fresh SensorBus per test.

Inputs: none (fixture definitions only).
Outputs: pytest fixtures `test_cfg`, `bus`.
"""

from __future__ import annotations

from typing import Iterator

import pytest

from sensors.sensor_bus import SensorBus


@pytest.fixture
def test_cfg() -> dict:
    """A minimal config dict covering only what the unit tests touch."""
    return {
        "event_bus": {"queue_max_size": 64, "history_buffer_size": 50},
        "instinct": {
            "reflex_urgency_threshold": 0.7,
            "reflex_cooldown_s": 0.05,
            "max_silent_s": 1.0,
        },
        "mood": {
            "baseline_valence": 0.55,
            "baseline_arousal": 0.35,
            "decay_half_life_s": 5.0,
            "tick_interval_s": 0.1,
            "states": {
                "sleepy_arousal_max": 0.2,
                "bored_arousal_max": 0.35,
                "bored_valence_max": 0.45,
                "annoyed_valence_max": 0.35,
                "excited_arousal_min": 0.75,
                "curious_valence_min": 0.55,
            },
            "event_deltas": {
                "bird_activity": {"valence": 0.08, "arousal": 0.10},
                "dog_activity": {"valence": 0.04, "arousal": 0.15},
                "person_recognized": {"valence": 0.15, "arousal": 0.10},
                "stranger_detected": {"valence": -0.05, "arousal": 0.25},
                "startle": {"valence": -0.25, "arousal": 0.6},
                "praise": {"valence": 0.3, "arousal": 0.1},
                "scold": {"valence": -0.3, "arousal": 0.1},
                "long_idle": {"valence": -0.05, "arousal": -0.1},
            },
        },
        "operating_mode": {
            "default": "normal",
            "privacy": {
                "disable_cloud_llm": True,
                "disable_audio_recording_persist": True,
                "face_indicator_color": "#FF00AA",
            },
            "debug": {"verbose_event_log": True, "show_internal_state_on_face": True},
        },
        "memory": {
            "episodic": {
                "db_path": ":memory:",
                "retention_days_default": 30,
                "retention_days_notable": 365,
                "notability_score_min": 0.6,
            },
            "semantic": {"db_path": ":memory:", "max_facts_per_subject": 500},
            "people": {"db_path": ":memory:"},
            "consolidation": {"run_interval_s": 3600, "min_repeats_for_pattern": 3},
        },
        "brain": {
            "inspector": {"relevance_min_score": 0.4, "contradiction_block": True},
        },
    }


@pytest.fixture
def bus(test_cfg: dict) -> Iterator[SensorBus]:
    b = SensorBus.from_config(test_cfg)
    b.start()
    yield b
    b.stop()