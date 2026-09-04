"""
brain/gemini_client.py

Cloud LLM client (Gemini). Only ever called by llm_router.py, and only
when: local confidence was too low, we are NOT in privacy mode, and we're
within the daily cloud-call budget (config: brain.llm_router.
cloud_daily_call_budget). This module has no opinion about any of that —
it just makes the call when asked.

Inputs: a fully-built prompt string (from brain/prompt_builder.py).
Outputs: LLMResult(text, confidence) — confidence is typically fixed near
         1.0 for cloud results, since the router already decided it trusts
         the cloud path.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from brain.local_llm import LLMResult  # reuse the same result shape


class GeminiClient:
    def __init__(self, cfg: dict):
        self.cfg = cfg["brain"]["gemini"]
        self._api_key = os.getenv("GEMINI_API_KEY", "")
        self._client = None  # lazy-init

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        # SENSOR INPUT HOOK (external API, not sensor): initialize the real
        # Gemini SDK client here using self._api_key and self.cfg["model"].
        self._client = "stub-client"

    def generate(self, prompt: str) -> LLMResult:
        self._ensure_client()
        if not self._api_key:
            return LLMResult(text="(no GEMINI_API_KEY set — stub response)", confidence=0.0)
        # SENSOR INPUT HOOK: real API call goes here, respecting
        # self.cfg["max_tokens"], self.cfg["temperature"], self.cfg["timeout_s"].
        return LLMResult(text="(gemini stub response)", confidence=1.0)
