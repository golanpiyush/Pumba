"""
voice/stt_whisper.py

Speech-to-text via a local Whisper model. Subscribes to
voice.utterance_captured (produced by vad.py) and transcribes it. Runs
locally by default (config: voice.stt.device) so no audio needs to leave
the device for basic transcription — this matters both for latency and for
privacy mode, which additionally disables *persisting* raw audio
(operating_mode.privacy.disable_audio_recording_persist) even though
transcription itself may still run locally.

Inputs: Event(topic="voice.utterance_captured").
Outputs: Event(topic="voice.transcript_ready") — this is one of the two
         event types brain/personality.py treats as "needs deliberation"
         and routes toward llm_router.py.
"""

from __future__ import annotations

from sensors.sensor_bus import SensorBus, Event


class WhisperSTT:
    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg["voice"]["stt"]
        self.bus = bus
        self._model = None

    def start(self) -> None:
        self.bus.subscribe("voice.utterance_captured", self._on_utterance)

    def stop(self) -> None:
        pass

    def _ensure_model_loaded(self) -> None:
        if self._model is not None:
            return
        # SENSOR INPUT HOOK: load a real whisper model (e.g. faster-whisper)
        # sized per self.cfg["model_size"] on self.cfg["device"].
        self._model = "stub-loaded"

    def _on_utterance(self, event: Event) -> None:
        self._ensure_model_loaded()
        audio_bytes = event.payload.get("audio_bytes", b"")
        text = self._transcribe(audio_bytes)
        if not text.strip():
            return
        self.bus.publish(Event(
            topic="voice.transcript_ready",
            payload={"text": text},
            urgency=0.5,
            source="stt_whisper",
        ))

    def _transcribe(self, audio_bytes: bytes) -> str:
        # SENSOR INPUT HOOK: real whisper inference call goes here.
        return ""