"""Run the planner from a terminal (requires configured API keys)."""

import argparse
import json
import sys
from pathlib import Path

# Make `python scripts/run_agent.py` work without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.graph import run_plan


def show(event: dict) -> None:
    data = event["data"]
    if event["event"] == "status":
        print(f"[status] {data['stage']}: {data['message']}")
    elif event["event"] == "log":
        kind = data["kind"]
        labels = {"tool_call": "Tool Call", "tool_output": "Tool Output", "thinking": "Thinking", "decision": "Decision"}
        payload = data.get("message") or data.get("summary") or json.dumps(data.get("args", {}), ensure_ascii=False)
        tool = f" {data['tool']}" if data.get("tool") else ""
        print(f"[{labels[kind]}]{tool} {payload}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--nights", type=int, required=True)
    parser.add_argument("--party", type=int, required=True)
    parser.add_argument("--budget", type=int, required=True)
    parser.add_argument("--persona", choices=["mass_centered", "walking", "frugal"], required=True)
    parser.add_argument("--preferences", default="")
    args = parser.parse_args()
    output = run_plan({"region": args.region, "start_date": args.start, "nights": args.nights,
                       "party_size": args.party, "budget_per_person": args.budget,
                       "persona": args.persona, "preferences": args.preferences}, show)
    print(json.dumps(output["plan"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
