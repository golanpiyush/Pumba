"""
brain/local_llm.py

Wrapper around a small local/on-device language model (e.g. a quantized
GGUF model run via llama.cpp bindings) — the first stop for anything
llm_router.py escalates. Cheap, private, always available (no network
dependency), but lower quality than the cloud model.

Inputs: a fully-built prompt string (from brain/prompt_builder.py).
Outputs: LLMResult(text, confidence) — confidence is a rough self-estimate
         used by llm_router.py to decide whether to escalate further.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LLMResult:
    text: str
    confidence: float  # 0.0-1.0, router escalates to cloud below the configured threshold


class LocalLLM:
    def __init__(self, cfg: dict):
        self.cfg = cfg["brain"]["local_llm"]
        self._model = None  # lazy-loaded on first generate() call

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        # SENSOR INPUT HOOK (model load, not sensor, but same "plug in real
        # thing here" spirit): load a llama-cpp-python model from
        # self.cfg["model_path"].
        self._model = "stub-loaded"

    def generate(self, prompt: str) -> LLMResult:
        self._ensure_loaded()
        # SENSOR INPUT HOOK: real inference call goes here, respecting
        # self.cfg["max_tokens"], self.cfg["temperature"], self.cfg["timeout_s"].
        return LLMResult(text="(local model stub response)", confidence=0.5)
