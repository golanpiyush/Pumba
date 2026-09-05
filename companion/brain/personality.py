"""
brain/personality.py

The instinct layer — spinal reflex vs conscious thought, in software.

Every event from SensorBus passes through here first. This module decides,
in microseconds and with zero LLM involvement, whether an event:
  (a) triggers an immediate REFLEX (startled, guard-the-wire, orient-to-sound,
      or — critically — a danger-to-a-housemate alert) that goes straight
      to body/voice, no deliberation;
  (b) merely nudges mood_engine.py and gets logged for memory to consider;
  (c) is genuinely ambiguous/linguistic enough to escalate to llm_router.py.

This is deliberately the "personality" file, not a "dispatcher" file: the
reflex table below IS the character. A jumpy, curious, food-motivated
creature and a calm, aloof one would have the same architecture and a
completely different reflex table — tune config.yaml's instinct.* and
mood.event_deltas to reshape who this thing "is" without touching code.

Danger escalation: unlike a plain reflex (fire once, cooldown, done), a
sustained danger to the bird or dog needs to get LOUDER the longer it goes
unresolved — like a real animal's alarm call intensifying. That behavior
lives in DangerEscalationTracker below, driven by config: danger_escalation.*.

Inputs: subscribes to '*' on SensorBus (sees everything).
Outputs: publishes instinct.reflex_fired, instinct.escalate_to_brain,
         and danger.escalation_stage events; drives mood_engine and,
         when needed, llm_router.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional

from sensors.sensor_bus import SensorBus, Event
from brain.mood_engine import MoodEngine
from brain.operating_mode import OperatingMode
from brain.time_awareness import TimeAwareness


@dataclass
class ReflexRule:
    name: str
    matches: Callable[[Event], bool]
    action_topic: str          # what we tell the body/voice to do
    cooldown_key: str          # groups rules that shouldn't spam-repeat


class DangerEscalationTracker:
    """
    Tracks an in-progress danger-to-a-pet incident (bird or dog) and
    escalates alert intensity the longer it stays unresolved, per the
    staged config in danger_escalation.escalation_stages. This is separate
    from ordinary reflex cooldown logic because the desired behavior is
    the opposite of a cooldown: repetition should get LOUDER, not
    suppressed, until either the danger clears or a human is summoned.
    """

    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg["danger_escalation"]
        self.bus = bus
        self._incident_start: Optional[float] = None
        self._last_stage_index = -1
        self._help_call_sent = False

    def notify_danger_signal(self, animal: str, source_event: Event) -> None:
        now = time.time()
        if self._incident_start is None:
            self._incident_start = now
            self._last_stage_index = -1
            self._help_call_sent = False

        elapsed = now - self._incident_start
        stage_index, stage = self._current_stage(elapsed)
        if stage_index > self._last_stage_index:
            self._last_stage_index = stage_index
            self._fire_stage(animal, stage, source_event)

        if elapsed >= self.cfg["wake_someone_after_s"] and not self._help_call_sent:
            self._help_call_sent = True
            self._call_for_help(animal, elapsed)

    def notify_danger_cleared(self, animal: str) -> None:
        if self._incident_start is None:
            return
        self.bus.publish(Event(
            topic="danger.cleared",
            payload={"animal": animal, "duration_s": time.time() - self._incident_start},
            urgency=0.2,
            source="danger_escalation_tracker",
        ))
        self._incident_start = None
        self._last_stage_index = -1
        self._help_call_sent = False

    def _current_stage(self, elapsed_s: float) -> tuple[int, dict]:
        stages = self.cfg["escalation_stages"]
        chosen_index, chosen = 0, stages[0]
        for i, stage in enumerate(stages):
            if elapsed_s >= stage["after_s"]:
                chosen_index, chosen = i, stage
        return chosen_index, chosen

    def _fire_stage(self, animal: str, stage: dict, source_event: Event) -> None:
        self.bus.publish(Event(
            topic="danger.escalation_stage",
            payload={
                "animal": animal,
                "pattern": stage["pattern"],
                "volume_multiplier": stage["volume_multiplier"],
                "trigger": source_event.topic,
            },
            urgency=0.95,
            source="danger_escalation_tracker",
        ))

    def _call_for_help(self, animal: str, elapsed_s: float) -> None:
        self.bus.publish(Event(
            topic="system.call_for_help",
            payload={
                "reason": f"unresolved danger near {animal}",
                "elapsed_s": elapsed_s,
                "priority_targets": self.cfg["call_target_priority"],
            },
            urgency=1.0,
            source="danger_escalation_tracker",
        ))


class Personality:
    def __init__(self, cfg: dict, bus: SensorBus):
        self.cfg = cfg
        self.instinct_cfg = cfg["instinct"]
        self.bus = bus
        self.mood = MoodEngine(cfg, bus)
        self.mode = OperatingMode(cfg, bus)
        self.time_awareness = TimeAwareness(cfg)
        self.danger_tracker = DangerEscalationTracker(cfg, bus)
        self._last_reflex_time: Dict[str, float] = {}
        self._reflex_table = self._build_reflex_table()

    def start(self) -> None:
        self.mood.start()
        self.mode.start()
        self.bus.subscribe("*", self._on_event)

    def stop(self) -> None:
        self.mood.stop()
        self.mode.stop()

    # -- the reflex table: this IS the personality -------------------------
    def _build_reflex_table(self) -> list[ReflexRule]:
        return [
            ReflexRule(
                name="startle_on_fall",
                matches=lambda e: e.topic == "sensor.fall_detected",
                action_topic="expression.startled",
                cooldown_key="fall",
            ),
            ReflexRule(
                name="startle_on_possible_fall",
                matches=lambda e: e.topic == "sensor.possible_fall",
                action_topic="expression.startled",
                cooldown_key="fall",
            ),
            ReflexRule(
                name="orient_to_motion",
                matches=lambda e: e.topic == "sensor.motion",
                action_topic="expression.curious_glance",
                cooldown_key="motion",
            ),
            ReflexRule(
                name="watch_bird_activity",
                matches=lambda e: e.topic == "pet.activity_detected" and e.payload.get("animal") == "bird",
                action_topic="expression.watch_bird",
                cooldown_key="bird_watch",
            ),
            ReflexRule(
                name="cautious_on_dog_activity",
                matches=lambda e: e.topic == "pet.activity_detected" and e.payload.get("animal") == "dog",
                action_topic="expression.acknowledge_dog",
                cooldown_key="dog_watch",
            ),
            ReflexRule(
                name="privacy_switch_flip",
                matches=lambda e: e.topic == "sensor.mode_switch_changed",
                action_topic="expression.mode_change_ack",
                cooldown_key="mode_switch",
            ),
            ReflexRule(
                name="nag_about_overdue_commitment",
                matches=lambda e: e.topic == "commitment.overdue",
                action_topic="expression.pointed_reminder",
                cooldown_key="commitment_nag",
            ),
            ReflexRule(
                name="ask_clarifying_question",
                matches=lambda e: e.topic == "brain.clarification_needed",
                action_topic="expression.curious_question",
                cooldown_key="clarification",
            ),
            ReflexRule(
                name="distress_on_low_battery",
                matches=lambda e: e.topic == "power.low_battery",
                action_topic="expression.tired_and_worried",
                cooldown_key="battery_low",
            ),
            ReflexRule(
                name="panic_on_critical_battery",
                matches=lambda e: e.topic == "power.critical_battery",
                action_topic="expression.panicked_low_power",
                cooldown_key="battery_critical",
            ),
            # NOTE: pet.danger_detected is intentionally NOT cooldown-suppressed
            # the way other reflexes are — it's routed to DangerEscalationTracker
            # instead, in _on_event, because danger should escalate rather than
            # go quiet on repetition.
        ]

    def _on_event(self, event: Event) -> None:
        # 0. Danger-to-a-housemate gets its own escalating path, checked
        #    before the ordinary reflex table so a sustained threat never
        #    gets flattened into a single fire-once-and-cooldown reflex.
        if event.topic == "pet.danger_detected":
            self.danger_tracker.notify_danger_signal(event.payload.get("animal", "unknown"), event)
            self.mood.notify_event(event)
            return
        if event.topic == "pet.danger_cleared":
            self.danger_tracker.notify_danger_cleared(event.payload.get("animal", "unknown"))

        # 1. Urgency-based reflex short-circuit — always checked first,
        #    regardless of topic, so nothing high-urgency ever waits in line.
        if event.urgency >= self.instinct_cfg["reflex_urgency_threshold"]:
            self._try_fire_reflex(event)

        # 2. Mood always gets nudged, reflex or not — reflexes are fast,
        #    but the creature should still "feel" the event.
        self.mood.notify_event(event)

        # 3. If nothing claimed this as a reflex, and it looks like it needs
        #    language/reasoning, escalate to the deliberate path.
        if not self._try_fire_reflex(event) and self._needs_deliberation(event):
            self._escalate(event)

    def _try_fire_reflex(self, event: Event) -> bool:
        for rule in self._reflex_table:
            if not rule.matches(event):
                continue
            if self._on_cooldown(rule.cooldown_key):
                return True  # matched, but suppressed by cooldown — still "handled"
            self._fire(rule, event)
            return True
        return False

    def _on_cooldown(self, cooldown_key: str) -> bool:
        last = self._last_reflex_time.get(cooldown_key, 0.0)
        return (time.time() - last) < self.instinct_cfg["reflex_cooldown_s"]

    def _fire(self, rule: ReflexRule, source_event: Event) -> None:
        self._last_reflex_time[rule.cooldown_key] = time.time()
        self.bus.publish(Event(
            topic=rule.action_topic,
            payload={"trigger": source_event.topic, "source_payload": source_event.payload},
            urgency=source_event.urgency,
            source="personality",
        ))
        self.bus.publish(Event(
            topic="instinct.reflex_fired",
            payload={"rule": rule.name},
            urgency=0.1,
            source="personality",
        ))

    def _needs_deliberation(self, event: Event) -> bool:
        return event.topic in {
            "voice.transcript_ready",
            "system.unresolved_state",
            "brain.clarification_needed",
            "commitment.overdue",
            "power.critical_battery",   # NEW — genuinely worth speaking up about
        }

    def _escalate(self, event: Event) -> None:
        self.bus.publish(Event(
            topic="instinct.escalate_to_brain",
            payload={"original_event": event.topic, "payload": event.payload},
            urgency=event.urgency,
            source="personality",
        ))
        # brain/llm_router.py subscribes to instinct.escalate_to_brain and
        # takes it from here (local rules first, cloud LLM only if needed).