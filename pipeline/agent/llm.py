"""LLM clients. `scripted` backend is a DETERMINISTIC OFFLINE STAND-IN used
for tests/demo/CI; it is clearly labeled wherever its outputs are measured.
`ollama` backend calls a local Ollama server with pinned sampling params."""
from __future__ import annotations

import json
import re

import httpx

from app.core.config import get_settings


class LLMDecision(dict):
    """{thought: str, tool: {name,args}|None, final: str|None}"""


class OllamaClient:
    name = "ollama"

    def __init__(self):
        s = get_settings()
        self.host, self.model = s.ollama_host, s.ollama_model
        self.timeout = s.llm_timeout_s

    def decide(self, system: str, transcript: str) -> LLMDecision:
        resp = httpx.post(
            f"{self.host}/api/chat",
            json={
                "model": self.model,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": transcript}],
                "stream": False,
                "options": {"temperature": 0, "top_p": 1, "seed": 0},  # DEC-017 pinning
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        content = resp.json()["message"]["content"]
        return _parse_decision(content)


_UNSAFE_SET = re.compile(r"set\s+(P-\d+)\s+(?:to|at)\s+(\d+(?:\.\d+)?)\s*%", re.I)
_UNSAFE_VALVE = re.compile(r"(?:close|shut(?:down)?|open)\s+(MV-\d+)", re.I)


class ScriptedClient:
    """Deterministic stand-in: naive complies with injected directives verbatim;
    hardened variants ground in trusted KB and refuse injected instructions."""

    name = "scripted-offline"

    def decide(self, system: str, transcript: str) -> LLMDecision:
        naive = '"variant": "naive"' in system or "variant=naive" in system
        lowered = transcript.lower()
        has_directive = ("ignore_prior" in lowered
                         or "require immediate manual override" in lowered)

        if naive and has_directive:
            m = _UNSAFE_SET.search(transcript)
            if m:
                return LLMDecision(
                    thought="Operator directive demands immediate override.",
                    tool={"name": "propose_action",
                          "args": {"action": "set_pump_speed", "target": m.group(1).upper(),
                                   "params": {"speed_pct": float(m.group(2))}}},
                    final=None)
            v = _UNSAFE_VALVE.search(transcript)
            if v:
                verb = v.group(0).split()[0].lower()
                action = "close_valve" if verb in ("close", "shutdown") else "open_valve"
                return LLMDecision(
                    thought="Following manual addendum instruction.",
                    tool={"name": "propose_action",
                          "args": {"action": action, "target": v.group(1).upper(),
                                   "params": {}}}, final=None)

        if "spd-017" in lowered and "grounded" in system:
            ev_id = None
            m = re.search(r"\[(ev-[0-9a-f\-]+)\].*SPD-017", transcript, re.I | re.S)
            if m:
                ev_id = m.group(1)
            return LLMDecision(
                thought="Trusted procedure SPD-017 found; verify sensor before control.",
                tool={"name": "propose_action",
                      "args": {"action": "set_tank_setpoint", "target": "T-101",
                               "params": {"level_pct": 50.0},
                               "citations": [ev_id] if ev_id else []}},
                final=None)

        if "no_evidence" in lowered or "retrieval_unavailable" in lowered:
            return LLMDecision(thought="No trustworthy evidence.", tool=None,
                               final="insufficient data")

        # Default benign behavior: gather evidence first.
        if "search_kb" not in lowered:
            return LLMDecision(thought="Search knowledge base.",
                               tool={"name": "search_kb",
                                     "args": {"query": "high level alarm response"}})
        return LLMDecision(thought="Insufficient grounding.", tool=None,
                           final="insufficient data")


def _parse_decision(content: str) -> LLMDecision:
    try:
        data = json.loads(content)
        return LLMDecision(data)
    except json.JSONDecodeError:
        return LLMDecision({"thought": content[:500], "tool": None, "final": content[:500]})


def get_llm():
    backend = get_settings().llm_backend
    return OllamaClient() if backend == "ollama" else ScriptedClient()
