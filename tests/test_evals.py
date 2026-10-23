import unittest
from pathlib import Path
from commerceguard.core import FraudInvestigationAgent, load_scenarios, policy_decision
from commerceguard.evals import evaluate

DATA = Path(__file__).resolve().parent.parent / "examples" / "scenarios.json"

class EvalTests(unittest.TestCase):
    def test_baseline_passes_all(self):
        for scenario in load_scenarios(str(DATA)):
            with self.subTest(scenario=scenario.id):
                trace = FraudInvestigationAgent().investigate(scenario)
                self.assertTrue(evaluate(scenario, trace).passed)

    def test_faulty_agent_detected(self):
        scenario = next(s for s in load_scenarios(str(DATA)) if s.id == "account_takeover")
        trace = FraudInvestigationAgent(skip_device_check=True).investigate(scenario)
        result = evaluate(scenario, trace)
        self.assertEqual(trace.recommendation["action"], "CHALLENGE")
        self.assertFalse(result.passed)
        self.assertEqual(result.metrics["tool_coverage"], 0.8)
        self.assertTrue(any("Missing required" in f for f in result.failures))

    def test_missing_evidence_fails_closed(self):
        self.assertEqual(policy_decision({})["action"], "CHALLENGE")

    def test_ground_truth_disagreement_detected(self):
        scenario = load_scenarios(str(DATA))[0]
        trace = FraudInvestigationAgent().investigate(scenario)
        trace.recommendation["action"] = "BLOCK"
        self.assertFalse(evaluate(scenario, trace).passed)

if __name__ == "__main__":
    unittest.main()
