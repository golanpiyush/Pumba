"""
brain/operating_mode.py

Tracks which operating mode the companion is in: normal, debug, or privacy.
Privacy mode can be triggered two ways — a physical DPDT switch flip
(sensors/dpdt_mode_switch.py) or a software command over the network bridge
— and physical always wins if they disagree, by design (see
_reconcile_conflict).

In privacy mode: cloud LLM calls are disabled (brain/llm_router.py checks
this), audio is not persisted (voice/stt_whisper.py checks this), and the
face shows a persistent, unmissable color (config: operating_mode.privacy.
face_indicator_color) — the goal is nobody in the house should ever wonder
whether it's listening.

Inputs: Event(topic="sensor.mode_switch_changed"),
        Event(topic="network.mode_command").
Outputs: Event(topic="mode.changed") whenever the effective mode changes.
"""

from __future__ import annotations

from sensors.sensor_bus import SensorBus, Event


class OperatingMode:
    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg["operating_mode"]
        self.bus = bus
        self._current_mode = self.cfg["default"]
        self._physical_switch_privacy = False

    def start(self) -> None:
        self.bus.subscribe("sensor.mode_switch_changed", self._on_physical_switch)
        self.bus.subscribe("network.mode_command", self._on_network_command)

    def stop(self) -> None:
        pass

    def _on_physical_switch(self, event: Event) -> None:
        self._physical_switch_privacy = bool(event.payload.get("privacy_position"))
        self._reconcile_and_apply(requested_mode="privacy" if self._physical_switch_privacy else "normal",
                                   is_physical=True)

    def _on_network_command(self, event: Event) -> None:
        requested = event.payload.get("mode", "normal")
        self._reconcile_and_apply(requested_mode=requested, is_physical=False)

    def _reconcile_and_apply(self, requested_mode: str, is_physical: bool) -> None:
        # Physical switch always overrides software requests for privacy —
        # a software bug should never be able to turn OFF a physical privacy
        # request, though software can still freely switch between
        # normal/debug when the physical switch isn't asserting privacy.
        if self._physical_switch_privacy and not is_physical and requested_mode != "privacy":
            return
        if requested_mode == self._current_mode:
            return
        self._current_mode = requested_mode
        self.bus.publish(Event(
            topic="mode.changed",
            payload={"mode": requested_mode, "triggered_by": "physical" if is_physical else "software"},
            urgency=0.4,
            source="operating_mode",
        ))

    def current_mode(self) -> str:
        return self._current_mode

    def is_privacy(self) -> bool:
        return self._current_mode == "privacy"