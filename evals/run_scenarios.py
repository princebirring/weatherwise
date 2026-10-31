"""Run the scenario suite against the real agents (needs Bedrock access; plan §16.3).

    CLIMATE_AGENT_MODEL_ID=<id> uv run python evals/run_scenarios.py [--only A1-04,INJ-01] [--judge]

Each case: a fresh agent team with the real Climate Risk MCP tools. Scored by
1) deterministic checks (tools, required/forbidden phrases, the Evaluator's code rules), and
2) with --judge, an AI judge (strands-evals OutputEvaluator) against the case rubric.
The report (pass rate by part and status) is written to evals/reports/.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evals.scenario_checks import check_reply, load_scenarios  # noqa: E402
from weatherwise.agents.message_rules import MessageRules  # noqa: E402
from weatherwise.agents.orchestrator import bedrock_model, build_team, climate_risk_client, mcp_tool_caller  # noqa: E402

REPORTS = Path(__file__).parent / "reports"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--only", help="comma-separated case ids")
    p.add_argument("--judge", action="store_true", help="also score with an AI judge (costs tokens)")
    args = p.parse_args()

    cases = load_scenarios()
    if args.only:
        wanted = set(args.only.split(","))
        cases = [c for c in cases if c["id"] in wanted]
    model = bedrock_model()
    mcp = climate_risk_client()
    results = []
    with mcp:
        tools = mcp.list_tools_sync()
        policy = mcp_tool_caller(mcp)("message_policy", {"country_code": "in"})
        rules = MessageRules.from_policy(policy)
        for case in cases:
            team = build_team(model, tools, policy, language=case["language"])
            prompt = f"[Saved location: lat {case['lat']}, lon {case['lon']}] {case['message']}"
            out = team.reply(prompt)
            called = [s["tool"] for s in out["steps"]]
            problems = check_reply(case, out["text"], called, rules)
            row = {"id": case["id"], "title": case["title"], "part": case["part"],
                   "expected_status": case["status"], "passed_checks": not problems,
                   "problems": problems, "tools": called, "used_fallback": out["used_fallback"],
                   "reply": out["text"]}
            if args.judge:
                from strands_evals import Case, Experiment
                from strands_evals.evaluators import OutputEvaluator

                exp = Experiment(cases=[Case(name=case["id"], input=prompt)],
                                 evaluators=[OutputEvaluator(rubric=case["rubric"], model=model)])
                report = exp.run_evaluations(lambda c, text=out["text"]: text)
                row["judge"] = json.loads(json.dumps(report.to_dict() if hasattr(report, "to_dict")
                                                     else str(report), default=str))
            results.append(row)
            print(f"{'PASS' if not problems else 'FAIL'} {case['id']:<7} {case['title']}"
                  + (f"  -> {problems}" if problems else ""))

    passed = sum(r["passed_checks"] for r in results)
    REPORTS.mkdir(exist_ok=True)
    path = REPORTS / f"scenarios_{datetime.now():%Y%m%d_%H%M}.json"
    path.write_text(json.dumps({"passed": passed, "total": len(results), "results": results},
                               indent=1, ensure_ascii=False))
    print(f"\n{passed}/{len(results)} passed deterministic checks. Report: {path}")


if __name__ == "__main__":
    main()
