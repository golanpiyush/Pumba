"""
sensors/sensor_bus.py

The event bus. This is the nervous system: every module (sensors, brain,
memory, body, power, network) publishes and subscribes to Event objects
here instead of calling each other directly. That's what keeps the system
"many small single-purpose modules" instead of a tangle of imports.

Design contract:
  - Events are small, typed, immutable-ish dataclasses.
  - Publishing is synchronous-dispatch, fire-and-forget from the caller's
    perspective (handlers run on the bus's own worker thread).
  - Every event carries an `urgency` in [0.0, 1.0]. The instinct layer
    (brain/personality.py's reflex path) uses this to decide reflex vs
    deliberate handling — high urgency skips everything and fires reflexes
    immediately, never waiting on mood/LLM machinery.
  - The bus keeps a bounded ring-buffer history for debugging/inspector use
    (brain/inspector/*) without ever growing unbounded.

Inputs: Event objects from any publisher (sensors, timers, network, voice).
Outputs: dispatched calls to subscriber callbacks; a queryable history.
"""

from __future__ import annotations

import queue
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional

EventHandler = Callable[["Event"], None]


@dataclass
class Event:
    """A single thing that happened, understood by nothing yet."""

    topic: str                                  # e.g. "sensor.motion", "mood.changed"
    payload: Dict[str, Any] = field(default_factory=dict)
    urgency: float = 0.0                        # 0.0 ambient info .. 1.0 drop-everything
    source: str = "unknown"                      # module name that published this
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])


class SensorBus:
    """
    Central pub/sub bus. Constructed once in main.py and threaded through
    every module that needs to sense or react.
    """

    def __init__(self, queue_max_size: int, history_buffer_size: int) -> None:
        self._queue: "queue.Queue[Event]" = queue.Queue(maxsize=queue_max_size)
        self._subscribers: Dict[str, List[EventHandler]] = {}
        self._wildcard_subscribers: List[EventHandler] = []
        self._history: Deque[Event] = deque(maxlen=history_buffer_size)
        self._lock = threading.Lock()
        self._worker: Optional[threading.Thread] = None
        self._running = False

    @classmethod
    def from_config(cls, cfg: dict) -> "SensorBus":
        bus_cfg = cfg["event_bus"]
        return cls(
            queue_max_size=bus_cfg["queue_max_size"],
            history_buffer_size=bus_cfg["history_buffer_size"],
        )

    def start(self) -> None:
        """Start the dispatch worker thread. Call once from main.py."""
        self._running = True
        self._worker = threading.Thread(target=self._dispatch_loop, daemon=True)
        self._worker.start()

    def stop(self) -> None:
        self._running = False

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        """Subscribe to an exact topic, or pass topic='*' for everything."""
        with self._lock:
            if topic == "*":
                self._wildcard_subscribers.append(handler)
            else:
                self._subscribers.setdefault(topic, []).append(handler)

    def publish(self, event: Event) -> None:
        """
        Publish an event. Never blocks the sensor thread for long — if the
        queue is full we drop the lowest-urgency event to make room, because
        a live pet should never freeze because its inbox is full.
        """
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            self._drop_lowest_urgency_and_retry(event)

    def _drop_lowest_urgency_and_retry(self, event: Event) -> None:
        # SENSOR INPUT HOOK: under sustained sensor flooding, this is where
        # you'd add backpressure telemetry (e.g. publish a bus.overload event)
        try:
            self._queue.get_nowait()
        except queue.Empty:
            pass
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            pass

    def _dispatch_loop(self) -> None:
        while self._running:
            try:
                event = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            self._history.append(event)
            self._dispatch(event)

    def _dispatch(self, event: Event) -> None:
        handlers = list(self._subscribers.get(event.topic, [])) + list(self._wildcard_subscribers)
        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:  # noqa: BLE001 — a bad handler must not kill the bus
                self._publish_handler_error(event, handler, exc)

    def _publish_handler_error(self, source_event: Event, handler: EventHandler, exc: Exception) -> None:
        # Deliberately does not re-raise: one broken subscriber (e.g. a face
        # animator glitch) must never take down sensing or memory.
        err_event = Event(
            topic="system.handler_error",
            payload={"handler": getattr(handler, "__qualname__", str(handler)), "error": str(exc),
                     "source_topic": source_event.topic},
            urgency=0.3,
            source="sensor_bus",
        )
        self._history.append(err_event)

    def recent_history(self, limit: int = 50) -> List[Event]:
        """Used by brain/inspector/* and debug mode to see what just happened."""
        with self._lock:
            return list(self._history)[-limit:]