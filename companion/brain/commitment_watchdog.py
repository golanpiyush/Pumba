"""
brain/commitment_watchdog.py

The nagging conscience. Runs on a slow tick, checking every pending
commitment (memory/db_commitments.py) against two things: whether it's now
overdue past its grace period, and — separately — whether the environment
model already confirms it was fulfilled (e.g. a "put me in the cage"
commitment gets auto-fulfilled the moment environment context actually
shows cage placement, without needing you to say anything).

When a commitment goes overdue and hasn't been nagged about recently, this
fires a mood-appropriate complaint at a natural moment — not the instant
it expires (that would feel robotic/alarming), but the next time
personality.py is already producing some ambient reaction, so it reads as
"oh, by the way" rather than a timer going off.

Inputs: periodic poll of CommitmentsDB.pending_commitments(); subscribes to
        environment.location_changed to auto-fulfill placement-kind
        commitments.
Outputs: Event(topic="commitment.overdue") — consumed by personality.py's
         reflex/mood layer to produce an annoyed callback line; Event(
         topic="commitment.fulfilled").
"""

from __future__ import annotations

import threading
import time
from typing import Optional

from sensors.sensor_bus import SensorBus, Event
from memory.db_commitments import CommitmentsDB
from brain.time_awareness import TimeAwareness


class CommitmentWatchdog:
    def __init__(self, cfg: dict, bus: SensorBus, commitments_db: CommitmentsDB):
        self.cfg = cfg["commitment_watchdog"]
        self.bus = bus
        self.db = commitments_db
        self.time_awareness = TimeAwareness(cfg)
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> None:
        self.bus.subscribe("environment.location_changed", self._on_location_changed)
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _poll_loop(self) -> None:
        while self._running:
            time.sleep(self.cfg["check_interval_s"])
            self._check_overdue_commitments()

    def _check_overdue_commitments(self) -> None:
        now = time.time()
        for commitment in self.db.pending_commitments():
            if commitment["expected_by"] is None:
                continue
            overdue_since = commitment["expected_by"] + commitment["grace_period_s"]
            if now < overdue_since:
                continue
            last_nag = commitment["last_nagged_at"] or 0.0
            if (now - last_nag) < self.cfg["renag_interval_s"]:
                continue  # already nagged recently, don't repeat every tick

            minutes_overdue = round((now - commitment["expected_by"]) / 60)
            self.db.mark_nagged(commitment["id"])
            self.bus.publish(Event(
                topic="commitment.overdue",
                payload={
                    "commitment_id": commitment["id"],
                    "raw_text": commitment["raw_text"],
                    "kind": commitment["kind"],
                    "subject": commitment["subject"],
                    "minutes_overdue": minutes_overdue,
                    "human_time_ago": self.time_awareness.humanize_past_timestamp(commitment["expected_by"]),
                },
                urgency=self.cfg["overdue_urgency"],
                source="commitment_watchdog",
            ))

    def _on_location_changed(self, event: Event) -> None:
        new_location = event.payload.get("location")
        if new_location != "bird_cage":
            return
        for commitment in self.db.pending_commitments():
            if commitment["kind"] == "cage_placement":
                self.db.mark_fulfilled(commitment["id"])
                self.bus.publish(Event(
                    topic="commitment.fulfilled",
                    payload={"commitment_id": commitment["id"], "kind": commitment["kind"]},
                    urgency=0.2,
                    source="commitment_watchdog",
                ))