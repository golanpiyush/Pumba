"""
voice/tts_edge.py

Text-to-speech via edge-tts (or similar neural TTS). Subscribes to
brain.response_ready (final, inspector-approved text) and to reflex
expression events that carry a short spoken line, and speaks them aloud.

Voice selection respects per-person overrides (config: voice.tts.
per_person_voice_overrides_key, looked up in people/profiles.yaml) so the
companion's voice/rate can shift slightly depending on who it's addressing
— part of the voice-aware personality requirement.

Inputs: Event(topic="brain.response_ready"), Event(topic="expression.*")
        events that include a "speech" payload key.
Outputs: audible playback (no bus event on success); publishes
         Event(topic="voice.playback_failed") on failure so power/network
         issues don't fail silently.
"""

from __future__ import annotations

from sensors.sensor_bus import SensorBus, Event


class EdgeTTS:
    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg["voice"]["tts"]
        self.bus = bus

    def start(self) -> None:
        self.bus.subscribe("brain.response_ready", self._on_response_ready)

    def stop(self) -> None:
        pass

    def _on_response_ready(self, event: Event) -> None:
        text = event.payload.get("text", "")
        if not text:
            return
        self.speak(text, person_key=event.payload.get("person_key"))

    def speak(self, text: str, person_key: str | None = None) -> None:
        voice = self._resolve_voice(person_key)
        try:
            self._synthesize_and_play(text, voice)
        except Exception as exc:  # noqa: BLE001
            self.bus.publish(Event(
                topic="voice.playback_failed",
                payload={"error": str(exc), "text": text},
                urgency=0.3,
                source="tts_edge",
            ))

    def _resolve_voice(self, person_key: str | None) -> str:
        # SENSOR INPUT HOOK: real lookup into people/profiles.yaml's
        # per-person tts_voice override goes here; falls back to default.
        return self.cfg["default_voice"]

    def _synthesize_and_play(self, text: str, voice: str) -> None:
        # SENSOR INPUT HOOK: real edge-tts synthesis + audio playback call
        # goes here, using self.cfg["rate"].
        pass