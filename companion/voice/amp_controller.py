"""
voice/amp_controller.py

Translates an abstract "how loud should I be right now" signal into an
actual playback volume/gain applied before TTS or alert-sound playback.
This is what makes the danger escalation stages in config (chirp_alert ->
loud_distress -> sos_loop, each with a volume_multiplier) physically
audible rather than just internal bookkeeping — normal speech stays gentle
by default, but a real danger event pushes volume up in real time.

Inputs: Event(topic="danger.escalation_stage") (sets a temporary volume
        override), Event(topic="danger.cleared") (returns to baseline).
Outputs: physical amplifier/audio gain change (SENSOR INPUT HOOK); no bus
         events (leaf consumer). Exposes current_volume() for tts_edge.py
         and any alert-tone player to query before playback.
"""

from __future__ import annotations

from sensors.sensor_bus import SensorBus, Event


class AmpController:
    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg["voice"]["amp"]
        self.bus = bus
        self._baseline_volume = self.cfg["baseline_volume"]
        self._active_multiplier = 1.0

    def start(self) -> None:
        self.bus.subscribe("danger.escalation_stage", self._on_escalation_stage)
        self.bus.subscribe("danger.cleared", self._on_danger_cleared)
        self._apply_hardware_volume(self._baseline_volume)

    def stop(self) -> None:
        pass

    def _on_escalation_stage(self, event: Event) -> None:
        self._active_multiplier = event.payload.get("volume_multiplier", 1.0)
        target = min(self.cfg["max_volume"], self._baseline_volume * self._active_multiplier)
        self._apply_hardware_volume(target)

    def _on_danger_cleared(self, event: Event) -> None:  # noqa: ARG002
        self._active_multiplier = 1.0
        self._apply_hardware_volume(self._baseline_volume)

    def current_volume(self) -> float:
        return min(self.cfg["max_volume"], self._baseline_volume * self._active_multiplier)

    def _apply_hardware_volume(self, volume: float) -> None:
        # SENSOR INPUT HOOK: real amplifier gain control goes here — e.g.
        # a MAX9744 I2C volume-control amp, or software gain scaling
        # applied to the audio buffer before playback in tts_edge.py.
        pass

    def whisper_level(self) -> float:
        return self.cfg["whisper_volume"]

    def loud_level(self) -> float:
        return self.cfg["max_volume"]