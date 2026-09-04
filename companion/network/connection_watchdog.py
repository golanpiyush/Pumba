"""
network/connection_watchdog.py

Watches internet/local-network connectivity and treats prolonged
disconnection as a self-preservation event, not a silent failure — mirrors
power_manager.py's philosophy: a real pet notices when something's wrong
with its world and reacts visibly, rather than logging an error nobody
sees.

Inputs: periodic ping/reachability check against config: network.watchdog.
        ping_host.
Outputs: Event(topic="network.status_changed") on any transition;
         Event(topic="network.prolonged_outage") (high urgency) once offline
         longer than call_for_help_after_s, which brain/personality.py's
         reflex table can hook to trigger a "calling for help" expression.
"""

from __future__ import annotations

import threading
import time

from sensors.sensor_bus import SensorBus, Event


class ConnectionWatchdog:
    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg["network"]["watchdog"]
        self.bus = bus
        self._consecutive_misses = 0
        self._offline_since: float | None = None
        self._prolonged_outage_alerted = False
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._check_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _check_loop(self) -> None:
        while self._running:
            reachable = self._ping(self.cfg["ping_host"])
            self._process_result(reachable)
            time.sleep(self.cfg["check_interval_s"])

    def _ping(self, host: str) -> bool:
        # SENSOR INPUT HOOK: real reachability check (socket connect / ICMP
        # ping) to `host` goes here.
        return True

    def _process_result(self, reachable: bool) -> None:
        if reachable:
            self._handle_reachable()
        else:
            self._handle_unreachable()

    def _handle_reachable(self) -> None:
        was_offline = self._offline_since is not None
        self._consecutive_misses = 0
        self._offline_since = None
        self._prolonged_outage_alerted = False
        if was_offline:
            self.bus.publish(Event(
                topic="network.status_changed",
                payload={"online": True},
                urgency=0.3,
                source="connection_watchdog",
            ))

    def _handle_unreachable(self) -> None:
        self._consecutive_misses += 1
        if self._consecutive_misses < self.cfg["offline_after_missed"]:
            return
        if self._offline_since is None:
            self._offline_since = time.time()
            self.bus.publish(Event(
                topic="network.status_changed",
                payload={"online": False},
                urgency=0.5,
                source="connection_watchdog",
            ))
        elapsed = time.time() - self._offline_since
        if elapsed >= self.cfg["call_for_help_after_s"] and not self._prolonged_outage_alerted:
            self._prolonged_outage_alerted = True
            self.bus.publish(Event(
                topic="network.prolonged_outage",
                payload={"offline_seconds": elapsed},
                urgency=0.9,
                source="connection_watchdog",
            ))