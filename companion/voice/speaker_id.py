"""
voice/speaker_id.py

Speaker identification — matches captured audio against enrolled
voiceprints (stored under people/voiceprints/, referenced from
memory/db_people.py) to answer "who is talking?" This is what enables
voice-aware personality: a distinct tone per recognized family member, a
cautious/curious tone for unrecognized voices, and a private tone reserved
for the primary owner.

Runs in parallel with stt_whisper.py on the same captured utterance —
identity and content are independent questions.

Inputs: Event(topic="voice.utterance_captured").
Outputs: Event(topic="voice.speaker_recognized") with {"person_key",
         "confidence"}, or Event(topic="voice.stranger_detected") if no
         enrolled voiceprint matches above config's match_confidence_min.
"""

from __future__ import annotations

from pathlib import Path

from sensors.sensor_bus import SensorBus, Event


class SpeakerID:
    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg["voice"]["speaker_id"]
        self.bus = bus
        self._voiceprint_dir = Path(self.cfg["voiceprint_dir"])
        self._enrolled_voiceprints: dict[str, object] = {}

    def start(self) -> None:
        self._load_enrolled_voiceprints()
        self.bus.subscribe("voice.utterance_captured", self._on_utterance)

    def stop(self) -> None:
        pass

    def _load_enrolled_voiceprints(self) -> None:
        if not self._voiceprint_dir.exists():
            return
        for path in self._voiceprint_dir.glob("*.npy"):
            person_key = path.stem
            # SENSOR INPUT HOOK: real voiceprint embedding load goes here.
            self._enrolled_voiceprints[person_key] = None

    def _on_utterance(self, event: Event) -> None:
        audio_bytes = event.payload.get("audio_bytes", b"")
        person_key, confidence = self._match_voiceprint(audio_bytes)
        if person_key and confidence >= self.cfg["match_confidence_min"]:
            self.bus.publish(Event(
                topic="voice.speaker_recognized",
                payload={"person_key": person_key, "confidence": confidence},
                urgency=0.4,
                source="speaker_id",
            ))
        else:
            self.bus.publish(Event(
                topic="voice.stranger_detected",
                payload={"confidence": confidence},
                urgency=0.5,
                source="speaker_id",
            ))

    def _match_voiceprint(self, audio_bytes: bytes) -> tuple[str | None, float]:
        # SENSOR INPUT HOOK: real embedding extraction + nearest-neighbor
        # match against self._enrolled_voiceprints goes here.
        return None, 0.0

    def enroll(self, person_key: str, audio_samples: list[bytes]) -> bool:
        if len(audio_samples) < self.cfg["enroll_min_samples"]:
            return False
        # SENSOR INPUT HOOK: real embedding computation + save to
        # self._voiceprint_dir / f"{person_key}.npy" goes here.
        return True