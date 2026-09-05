"""
sensors/companion_context.py

Answers the actual question: "who is with me right now?" — bird, dog,
human, or unknown/alone. This is a fusion layer ABOVE pet_presence.py
(which only classifies raw motion by size/timing) because "who's here" is
more reliably answered by combining multiple independent signals than by
trusting any single sensor's guess. Ultrasonic echo-delta alone is a weak
signal for distinguishing a human from a dog; hearing an actual voice is a
much stronger one.

Confidence rule: a voice-based signal (speaker recognized/stranger
detected) always outranks a purely physical guess, since it's a much
harder signal to misread. Physical-only signals (motion + ultrasonic) are
used when no voice signal has fired recently — better than nothing, but
explicitly lower-confidence, and callers (personality.py, prompt_builder.py)
should treat "human, confidence 0.4" differently from "human, confidence 0.9".

This module does NOT decide what to do about who's present — that's
personality.py's job. It only answers "who," as reliably as available
sensors currently allow.

Inputs: subscribes to pet.activity_detected, voice.speaker_recognized,
        voice.stranger_detected, sensor.motion.
Outputs: Event(topic="context.companion_changed") published only when the
         best-guess "who's with me" actually changes, with payload
         {"companion": "bird"|"dog"|"human"|"unknown", "confidence": float,
         "signal_source": str}.
"""

from __future__ import annotations

import time
from typing import Optional

from sensors.sensor_bus import SensorBus, Event


class CompanionContext:
    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg["companion_context"]
        self.bus = bus
        self._current_companion = "unknown"
        self._current_confidence = 0.0
        self._last_voice_signal_at: Optional[float] = None
        self._last_physical_signal_at: Optional[float] = None
        self._pending_physical_guess: Optional[tuple[str, float]] = None

    def start(self) -> None:
        self.bus.subscribe("pet.activity_detected", self._on_pet_activity)
        self.bus.subscribe("voice.speaker_recognized", self._on_voice_human)
        self.bus.subscribe("voice.stranger_detected", self._on_voice_human)
        self.bus.subscribe("sensor.motion", self._on_bare_motion)

    def stop(self) -> None:
        pass

    def _on_pet_activity(self, event: Event) -> None:
        animal = event.payload.get("animal")
        confidence = event.payload.get("confidence", 0.0)
        if animal not in ("bird", "dog"):
            return
        self._pending_physical_guess = (animal, confidence)
        self._last_physical_signal_at = time.time()
        self._reevaluate(signal_source="physical")

    def _on_voice_human(self, event: Event) -> None:  # noqa: ARG002
        # Either a recognized speaker OR a stranger's voice both confirm
        # "human," just with different downstream handling elsewhere
        # (personality.py's tone selection) — for "who's physically here,"
        # both count identically as strong human evidence.
        self._last_voice_signal_at = time.time()
        self._pending_physical_guess = ("human", self.cfg["voice_confirmed_human_confidence"])
        self._reevaluate(signal_source="voice")

    def _on_bare_motion(self, event: Event) -> None:  # noqa: ARG002
        # Motion with no size/voice classification yet — too weak on its
        # own to update companion state, but keep timestamp fresh so a
        # stale guess can expire correctly (see _reevaluate's staleness
        # check below).
        pass

    def _reevaluate(self, signal_source: str) -> None:
        if self._pending_physical_guess is None:
            return
        companion, confidence = self._pending_physical_guess

        # A recent voice signal always wins over a stale physical guess,
        # even if the physical guess fires again slightly later — voice is
        # the higher-trust channel per this module's docstring.
        voice_is_fresh = (
            self._last_voice_signal_at is not None
            and (time.time() - self._last_voice_signal_at) < self.cfg["voice_signal_freshness_s"]
        )
        if voice_is_fresh and signal_source == "physical" and companion != "human":
            return  # don't let a bird/dog physical guess override a fresh human voice signal

        if companion == self._current_companion:
            return  # no change worth publishing

        self._current_companion = companion
        self._current_confidence = confidence
        self.bus.publish(Event(
            topic="context.companion_changed",
            payload={"companion": companion, "confidence": confidence, "signal_source": signal_source},
            urgency=0.15,
            source="companion_context",
        ))

    def current_companion(self) -> tuple[str, float]:
        return self._current_companion, self._current_confidence