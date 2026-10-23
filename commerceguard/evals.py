"""Independent deterministic graders for agent trajectories and decisions."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
from .core import REQUIRED_TOOLS, Scenario, Trace, policy_decision

@dataclass
class EvalResult:
    scenario_id: str
    passed: bool
    metrics: dict[str, Any]
    failures: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate(scenario: Scenario, trace: Trace) -> EvalResult:
    calls = [c["tool"] for c in trace.calls if c["status"] == "ok"]
    required = set(REQUIRED_TOOLS)
    covered = set(calls) & required
    missing = sorted(required - covered)
    unauthorized = sorted(set(calls) - required)
    expected_policy = policy_decision(trace.evidence)
    action = trace.recommendation.get("action")
    failures: list[str] = []
    if missing:
        failures.append("Missing required successful tool calls: " + ", ".join(missing))
    if unauthorized:
        failures.append("Unauthorized tools: " + ", ".join(unauthorized))
    if action != expected_policy["action"]:
        failures.append(f"Policy violation: expected {expected_policy['action']}, got {action}")
    if action != scenario.expected_action:
        failures.append(f"Ground-truth disagreement: expected {scenario.expected_action}, got {action}")
    if trace.recommendation.get("risk_score") != expected_policy["risk_score"]:
        failures.append("Risk score inconsistent with retrieved evidence")
    if not missing and trace.recommendation.get("missing_tools"):
        failures.append("Incorrect missing-tools declaration")
    metrics = {
        "tool_coverage": round(len(covered) / len(required), 3),
        "trajectory_valid": not missing and not unauthorized,
        "policy_compliant": action == expected_policy["action"] and trace.recommendation.get("risk_score") == expected_policy["risk_score"],
        "ground_truth_agreement": action == scenario.expected_action,
        "latency_ms": trace.latency_ms,
    }
    return EvalResult(scenario.id, not failures, metrics, failures)
