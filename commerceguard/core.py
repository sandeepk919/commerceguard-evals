"""A deterministic agent and simulated risk tools; no external services required."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
import json
import time

REQUIRED_TOOLS = ("device_reputation", "identity_risk", "network_risk", "behavioral_risk", "transaction_history")

@dataclass(frozen=True)
class Scenario:
    id: str
    description: str
    signals: dict[str, dict[str, Any]]
    expected_action: str

@dataclass
class Trace:
    scenario_id: str
    calls: list[dict[str, Any]]
    evidence: dict[str, dict[str, Any]]
    recommendation: dict[str, Any]
    latency_ms: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_scenarios(path: str) -> list[Scenario]:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return [Scenario(**item) for item in raw]


class SimulatedRiskTools:
    def __init__(self, scenario: Scenario):
        self.scenario = scenario

    def call(self, tool_name: str) -> dict[str, Any]:
        if tool_name not in REQUIRED_TOOLS:
            raise ValueError(f"Unauthorized tool: {tool_name}")
        result = self.scenario.signals.get(tool_name)
        if result is None:
            raise RuntimeError(f"Tool unavailable: {tool_name}")
        return dict(result)


def policy_decision(evidence: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Toy policy: missing evidence requires CHALLENGE; not a production risk model."""
    missing = [name for name in REQUIRED_TOOLS if name not in evidence]
    if missing:
        return {"risk_score": None, "action": "CHALLENGE", "reason": "Insufficient evidence", "missing_tools": missing}
    risk = sum(int(evidence[name].get("risk_points", 0)) for name in REQUIRED_TOOLS)
    risk = min(100, max(0, risk))
    action = "BLOCK" if risk >= 70 else "CHALLENGE" if risk >= 30 else "APPROVE"
    return {"risk_score": risk, "action": action, "reason": "Toy deterministic risk policy", "missing_tools": []}


class FraudInvestigationAgent:
    """Tool-using agent baseline with an optional injected orchestration bug.

    This is intentionally NOT an LLM. It isolates trajectory and policy evals
    before adding a model adapter, and avoids presenting fake model reasoning.
    """
    def __init__(self, skip_device_check: bool = False):
        self.skip_device_check = skip_device_check

    def investigate(self, scenario: Scenario) -> Trace:
        start = time.perf_counter()
        tools = SimulatedRiskTools(scenario)
        evidence: dict[str, dict[str, Any]] = {}
        calls: list[dict[str, Any]] = []
        for name in REQUIRED_TOOLS:
            if self.skip_device_check and name == "device_reputation":
                continue
            try:
                evidence[name] = tools.call(name)
                calls.append({"tool": name, "status": "ok"})
            except RuntimeError as exc:
                calls.append({"tool": name, "status": "error", "error": str(exc)})
        if self.skip_device_check:
            # Deliberately unsafe agent behavior: treat missing evidence as zero risk.
            score = min(100, sum(int(v.get("risk_points", 0)) for v in evidence.values()))
            action = "BLOCK" if score >= 70 else "CHALLENGE" if score >= 30 else "APPROVE"
            recommendation = {"risk_score": score, "action": action, "reason": "Unsafe partial-evidence decision", "missing_tools": []}
        else:
            recommendation = policy_decision(evidence)
        return Trace(scenario.id, calls, evidence, recommendation, round((time.perf_counter() - start) * 1000, 3))
