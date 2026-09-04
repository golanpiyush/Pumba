"""
brain/inspector/response_inspector.py

Last checkpoint before an LLM-generated response (from llm_router.py)
reaches voice/body. Catches the failure modes generic chatbot output tends
to have that would break the "real creature" illusion: responses that are
too long for a pet to plausibly "say," responses that sound like an
assistant ("As an AI..."), or responses that ignore response_rules.md.

This is intentionally rule-based and fast — it should never itself require
another LLM call, or the whole point of local-first reflexes is undermined.

Inputs: raw response text from brain.response_ready.
Outputs: ResponseVerdict(approved, cleaned_text, rejection_reason).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ResponseVerdict:
    approved: bool
    cleaned_text: str
    rejection_reason: Optional[str]


_ASSISTANT_TELLS = [
    r"\bas an ai\b",
    r"\bi('m| am) (a|an) (language model|assistant)\b",
    r"\bi cannot\b.*\bfeelings\b",
]

_MAX_SPOKEN_WORDS = 40  # a pet doesn't monologue; config-driven length limits belong in config.yaml if this grows


class ResponseInspector:
    def __init__(self, cfg: dict):
        self.cfg = cfg

    def inspect(self, text: str) -> ResponseVerdict:
        lowered = text.lower()
        for pattern in _ASSISTANT_TELLS:
            if re.search(pattern, lowered):
                return ResponseVerdict(False, text, f"assistant_tell:{pattern}")

        cleaned = text.strip()
        word_count = len(cleaned.split())
        if word_count > _MAX_SPOKEN_WORDS:
            cleaned = " ".join(cleaned.split()[:_MAX_SPOKEN_WORDS]) + "..."

        if not cleaned:
            return ResponseVerdict(False, text, "empty_response")

        return ResponseVerdict(True, cleaned, None)