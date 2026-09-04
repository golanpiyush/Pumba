"""
network/remote_bridge.py

Lightweight server exposing the companion's state to a local companion
app/dashboard (e.g. for manual privacy-mode toggling, viewing recent
memory, or nudging mood for testing). Auth via REMOTE_BRIDGE_TOKEN (.env).
Deliberately thin: this module translates network requests into bus events
and bus events into pushed status — it holds no behavior logic itself.

Inputs: incoming requests/commands from a local client (e.g.
        {"command": "set_mode", "mode": "privacy"}).
Outputs: Event(topic="network.mode_command") and similar translated events;
         periodic Event(topic="network.heartbeat_sent") outward status push.
"""

from __future__ import annotations

import os
import threading
import time

from sensors.sensor_bus import SensorBus, Event


class RemoteBridge:
    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg["network"]["remote_bridge"]
        self.bus = bus
        self._auth_token = os.getenv("REMOTE_BRIDGE_TOKEN", "")
        self._server = None
        self._heartbeat_thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        self._server = self._init_server()
        self._running = True
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

    def stop(self) -> None:
        self._running = False

    def _init_server(self):
        # SENSOR INPUT HOOK: real HTTP/WebSocket server bind on
        # self.cfg["host"]:self.cfg["port"] goes here, routing authenticated
        # requests to self._handle_command.
        return None

    def _handle_command(self, command_payload: dict, provided_token: str) -> bool:
        if provided_token != self._auth_token:
            return False
        if command_payload.get("command") == "set_mode":
            self.bus.publish(Event(
                topic="network.mode_command",
                payload={"mode": command_payload.get("mode", "normal")},
                urgency=0.3,
                source="remote_bridge",
            ))
        return True

    def _heartbeat_loop(self) -> None:
        while self._running:
            time.sleep(self.cfg["heartbeat_interval_s"])
            self.bus.publish(Event(
                topic="network.heartbeat_sent",
                payload={},
                urgency=0.02,
                source="remote_bridge",
            ))