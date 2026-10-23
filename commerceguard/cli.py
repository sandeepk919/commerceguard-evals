"""CLI: python -m commerceguard.cli [--faulty] [--output path]."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .core import FraudInvestigationAgent, load_scenarios
from .evals import evaluate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run fraud agent and trajectory evaluations")
    parser.add_argument("--faulty", action="store_true", help="Inject a bug that skips device reputation")
    parser.add_argument("--dataset", default=str(Path(__file__).resolve().parent.parent / "examples" / "scenarios.json"))
    parser.add_argument("--output", default="results.json")
    args = parser.parse_args()
    agent = FraudInvestigationAgent(skip_device_check=args.faulty)
    records = []
    for scenario in load_scenarios(args.dataset):
        trace = agent.investigate(scenario)
        result = evaluate(scenario, trace)
        records.append({"scenario": scenario.id, "trace": trace.to_dict(), "eval": result.to_dict()})
        print(f"{'PASS' if result.passed else 'FAIL'} {scenario.id:20} action={trace.recommendation['action']:9} coverage={result.metrics['tool_coverage']:.0%}")
        for failure in result.failures:
            print("   - " + failure)
    output = {"mode": "faulty" if args.faulty else "baseline", "passed": sum(r["eval"]["passed"] for r in records), "total": len(records), "results": records}
    Path(args.output).write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"\n{output['passed']}/{output['total']} passed. Trace report: {args.output}")
    return 0 if output["passed"] == output["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
