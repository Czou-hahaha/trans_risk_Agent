#!/usr/bin/env python3
"""Run the deterministic investigation workflow."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_V1 = Path(__file__).resolve().parents[1]
if str(_V1) not in sys.path:
    sys.path.insert(0, str(_V1))

from dotenv import load_dotenv

load_dotenv(_V1 / ".env")

from workflow.runner import InvestigationWorkflowRunner  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run investigation workflow")
    parser.add_argument("--metric", default="fpd7")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = InvestigationWorkflowRunner(metric_name=args.metric).run()

    if args.json:
        print(result.model_dump_json(indent=2))
        return

    print(f"status: {result.workflow_status}")
    print(f"needs_investigation: {result.needs_investigation}")
    if result.investigation_conclusion:
        print(f"\n{result.investigation_conclusion.business_summary}")


if __name__ == "__main__":
    main()
