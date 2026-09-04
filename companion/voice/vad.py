"""
voice/vad.py

Voice Activity Detection — the gate that decides when audio is worth
running through STT at all. Runs continuously and cheaply (webrtcvad-style
frame classification); only when speech is detected and then a
silence_timeout_s gap occurs does this hand a complete utterance buffer to
stt_whisper.py. This keeps the (relatively expensive) STT model idle most
of the time, consistent with the "cheap local rules before expensive
processing" philosophy applied to audio too.

Inputs: raw audio frames from the microphone.
Outputs: Event(topic="voice.utterance_captured") with a raw audio buffer,
         consumed by stt_whisper.py and speaker_id.py in parallel.
"""

from __future__ import annotations

import threading
import time

from sensors.sensor_bus import SensorBus, Event


class VoiceActivityDetector:
    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg["voice"]["vad"]
        self.bus = bus
        self._thread: threading.Thread | None = None
        self._running = False
        self._speech_buffer: list[bytes] = []
        self._in_speech = False
        self._last_speech_time = 0.0

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _listen_loop(self) -> None:
        frame_interval = self.cfg["frame_ms"] / 1000.0
        while self._running:
            frame = self._read_audio_frame()
            if frame is not None:
                self._process_frame(frame)
            time.sleep(frame_interval)

    def _read_audio_frame(self) -> bytes | None:
        # SENSOR INPUT HOOK: real microphone frame capture goes here
        # (e.g. via pyaudio/sounddevice), sized per self.cfg["frame_ms"].
        return None

    def _process_frame(self, frame: bytes) -> None:
        is_speech = self._classify_frame(frame)
        if is_speech:
            self._speech_buffer.append(frame)
            self._in_speech = True
            self._last_speech_time = time.time()
        elif self._in_speech and (time.time() - self._last_speech_time) >= self.cfg["silence_timeout_s"]:
            self._emit_utterance()

    def _classify_frame(self, frame: bytes) -> bool:
        # SENSOR INPUT HOOK: real VAD classification (e.g. webrtcvad) using
        # self.cfg["aggressiveness"] goes here.
        return False

    def _emit_utterance(self) -> None:
        buffer = b"".join(self._speech_buffer)
        self._speech_buffer = []
        self._in_speech = False
        self.bus.publish(Event(
            topic="voice.utterance_captured",
            payload={"audio_bytes": buffer},
            urgency=0.4,
            source="vad",
        ))
