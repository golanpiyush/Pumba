"""
brain/llm_router.py

The escalation gate between "reflex/rules" and "actual language model."
Subscribes to instinct.escalate_to_brain (published by
brain/personality.py only for events that plausibly need language or
reasoning). Tries local_llm.py first; only calls out to gemini_client.py
when local confidence is too low AND we're not in privacy mode AND we're
under the daily cloud-call budget.

This is the chokepoint that keeps "most reactions are instant reflexes" true
in practice — nothing reaches here unless personality.py already decided
rules genuinely can't handle it.

Inputs: Event(topic="instinct.escalate_to_brain").
Outputs: Event(topic="brain.response_ready") with the generated reply/action,
         consumed by prompt_builder.py's caller and ultimately voice/body.
"""

from __future__ import annotations

from datetime import date

from sensors.sensor_bus import SensorBus, Event
from brain.local_llm import LocalLLM
from brain.gemini_client import GeminiClient
from brain.prompt_builder import PromptBuilder
from brain.operating_mode import OperatingMode


class LLMRouter:
    def __init__(self, cfg: dict, bus: SensorBus, operating_mode: OperatingMode):
        self.cfg = cfg["brain"]["llm_router"]
        self.bus = bus
        self.operating_mode = operating_mode
        self.local_llm = LocalLLM(cfg)
        self.gemini = GeminiClient(cfg)
        self.prompt_builder = PromptBuilder(cfg)
        self._cloud_calls_today = 0
        self._budget_date = date.today()

    def start(self) -> None:
        self.bus.subscribe("instinct.escalate_to_brain", self._on_escalation)

    def stop(self) -> None:
        pass

    def _on_escalation(self, event: Event) -> None:
        prompt = self.prompt_builder.build(trigger_event=event)
        local_result = self.local_llm.generate(prompt)

        if local_result.confidence >= self.cfg["local_confidence_escalate_below"] or not self.cfg["prefer_local_first"]:
            self._emit_response(local_result.text, source="local_llm")
            return

        if self.operating_mode.is_privacy():
            # Privacy mode: never leaves the device, even if local confidence
            # is low — fall back to the local model's best (if imperfect) guess.
            self._emit_response(local_result.text, source="local_llm_privacy_fallback")
            return

        if not self._within_cloud_budget():
            self._emit_response(local_result.text, source="local_llm_budget_exhausted")
            return

        cloud_result = self.gemini.generate(prompt)
        self._cloud_calls_today += 1
        self._emit_response(cloud_result.text, source="gemini")

    def _within_cloud_budget(self) -> bool:
        today = date.today()
        if today != self._budget_date:
            self._budget_date = today
            self._cloud_calls_today = 0
        return self._cloud_calls_today < self.cfg["cloud_daily_call_budget"]

    def _emit_response(self, text: str, source: str) -> None:
        self.bus.publish(Event(
            topic="brain.response_ready",
            payload={"text": text, "generated_by": source},
            urgency=0.3,
            source="llm_router",
        ))