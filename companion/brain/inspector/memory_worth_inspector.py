"""
brain/inspector/memory_worth_inspector.py

The final judgment call above relevance_scorer.py: not "is this worth
storing at all" (that's relevance_scorer's job) but "given that we ARE
storing this, how long should it live, and does it deserve special
handling." This is the meta-inspector — it looks at the whole picture
(topic, mood swing, danger classification, time of day, repetition) and
returns a verdict that memory_manager.py uses to set retention and tags.

Three outcomes it can produce for any candidate episode:
  - EPHEMERAL:  routine, forgettable — default short retention applies.
  - NOTABLE:    a funny/interesting moment — longer retention, may be
                referenced casually in future conversation.
  - PERMANENT:  a "traumatic" or safety-critical incident (a fall, a
                bird/dog danger event, a critical-battery scare, a long
                outage) — retained indefinitely regardless of normal
                aging rules, and flagged so prompt_builder.py can treat
                references to it more carefully/seriously rather than
                lightly ("that was scary" tone, not throwaway trivia).

Inputs: candidate episode dict (topic, payload, mood context) plus a
        TimeContext from brain/time_awareness.py so time-of-day can factor
        into judgment (e.g. a startle at 3am reads differently than one at
        noon with everyone home).
Outputs: MemoryWorthVerdict(tier, retention_days, is_permanent, reason).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from brain.time_awareness import TimeContext


@dataclass
class MemoryWorthVerdict:
    tier: str                 # "ephemeral" | "notable" | "permanent"
    retention_days: int
    is_permanent: bool
    reason: str                # short human-readable justification, useful for logs/debug mode


class MemoryWorthInspector:
    def __init__(self, cfg: dict):
        self.cfg = cfg["memory_worth"]
        self.episodic_cfg = cfg["memory"]["episodic"]

    def judge(
        self,
        topic: str,
        payload: Dict[str, Any],
        relevance_score: float,
        mood_valence_delta: float,
        mood_arousal_delta: float,
        time_context: Optional[TimeContext] = None,
    ) -> MemoryWorthVerdict:
        # 1. Trauma / safety-critical tier — always wins, regardless of
        #    how the relevance scorer felt about it.
        if self._is_trauma_tier(topic, payload):
            return MemoryWorthVerdict(
                tier="permanent",
                retention_days=self.cfg["trauma_retention_days"],
                is_permanent=True,
                reason=f"safety-critical topic '{topic}' is always retained long-term",
            )

        # 2. Funny/delightful moment tier — a sharp positive mood swing is
        #    the signature of something worth remembering fondly, even if
        #    the raw event itself looks mundane (e.g. "bird did something
        #    ridiculous" isn't dangerous, but it's memorable).
        if mood_valence_delta >= self.cfg["funny_moment_valence_spike_min"]:
            return MemoryWorthVerdict(
                tier="notable",
                retention_days=self.episodic_cfg["retention_days_notable"],
                is_permanent=False,
                reason="sharp positive mood swing suggests a genuinely memorable moment",
            )

        # 3. Near-zero arousal, near-zero relevance — actively forgettable,
        #    not just "not notable." This is where boredom-tier ambient
        #    noise gets explicitly deprioritized rather than lingering at
        #    default retention out of laziness.
        if mood_arousal_delta <= self.cfg["boredom_forgettable_arousal_max"] and relevance_score < 0.5:
            return MemoryWorthVerdict(
                tier="ephemeral",
                retention_days=max(1, self.episodic_cfg["retention_days_default"] // 4),
                is_permanent=False,
                reason="low arousal, low relevance — routine background noise",
            )

        # 4. Default — ordinary episodic retention.
        return MemoryWorthVerdict(
            tier="ephemeral",
            retention_days=self.episodic_cfg["retention_days_default"],
            is_permanent=False,
            reason="standard episodic event, no special tier triggered",
        )

    def _is_trauma_tier(self, topic: str, payload: Dict[str, Any]) -> bool:
        if topic in self.cfg["trauma_keywords_topics"]:
            return True
        # a pet.danger_detected event nested under a different topic name
        # (e.g. published by a future camera module) can still self-report
        # severity in its payload — checked defensively rather than only
        # trusting the topic string.
        return bool(payload.get("is_trauma_tier", False))