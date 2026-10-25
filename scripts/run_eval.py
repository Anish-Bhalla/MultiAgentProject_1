from __future__ import annotations
import asyncio
import json
from pathlib import Path
from app.agents.planner import make_plan

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "evaluation" / "datasets" / "routing_cases.json"


async def main() -> None:
    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    correct = 0
    rows = []
    for case in cases:
        plan = await make_plan(case["question"])
        actual = set(plan.get("tasks", []))
        expected = set(case["expected_tools"])
        passed = expected.issubset(actual)
        correct += int(passed)
        rows.append({"question": case["question"], "expected": sorted(expected), "actual": sorted(actual), "pass": passed})
    output = {"cases": len(rows), "passed": correct, "routing_recall": round(correct / max(1, len(rows)), 4), "results": rows}
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
