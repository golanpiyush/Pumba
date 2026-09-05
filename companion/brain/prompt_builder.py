"""
brain/prompt_builder.py

Assembles the final prompt sent to local_llm.py / gemini_client.py by
layering markdown fragments from prompts/ in a fixed order:

  core_identity.md
  + personality_quirks.md
  + mood/<current_mood>.md
  + modes/<current_operating_mode>.md
  + people/<recognized_person or stranger>.md
  + pets/<dog.md and/or bird.md, if relevant to the trigger>
  + response_rules.md
  + situational context (recent memory, trigger event)

Keeping this layering explicit (rather than one giant prompt file) is what
lets personality, mood, mode, and per-person tone all vary independently —
each concern owns one small file.

Inputs: trigger_event (the Event that caused escalation), plus current
        mood/mode/person context pulled from the relevant modules.
Outputs: a single assembled prompt string.
"""

from __future__ import annotations

from pathlib import Path

from sensors.sensor_bus import Event


class PromptBuilder:
    PROMPTS_DIR = Path("prompts")

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def build(
        self,
        trigger_event: Event,
        current_mood: str = "curious",
        current_mode: str = "normal",
        person_key: str = "stranger",
        relevant_pets: list[str] | None = None,
        memory_context: str = "",
        battery_percent: int | None = None,
    ) -> str:
        sections = [
            self._read("core_identity.md"),
            self._read("personality_quirks.md"),
            self._read(f"mood/{current_mood}.md"),
            self._read(f"modes/{current_mode}.md"),
            self._read(f"people/{person_key}.md"),
        ]
        for pet in relevant_pets or []:
            sections.append(self._read(f"pets/{pet}.md"))
        sections.append(self._read("response_rules.md"))
        sections.append(self._format_situation(trigger_event, memory_context))
        if battery_percent is not None:
            sections.append(f"## Physical state\nCurrent battery: {battery_percent}%")
        return "\n\n".join(s for s in sections if s)

    def _read(self, relative_path: str) -> str:
        path = self.PROMPTS_DIR / relative_path
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8").strip()

    def _format_situation(self, trigger_event: Event, memory_context: str) -> str:
        return (
            f"## Current situation\n"
            f"Trigger: {trigger_event.topic}\n"
            f"Details: {trigger_event.payload}\n"
            f"Relevant memory: {memory_context or '(none surfaced)'}"
        )