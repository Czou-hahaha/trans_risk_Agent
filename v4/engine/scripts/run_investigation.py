#!/usr/bin/env python3
"""Run the V4 deterministic investigation workflow (CLI)."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

_ENGINE = Path(__file__).resolve().parents[1]
_V4_ROOT = _ENGINE.parent
if str(_ENGINE) not in sys.path:
    sys.path.insert(0, str(_ENGINE))

from dotenv import load_dotenv

load_dotenv(_V4_ROOT / ".env")

from workflow.investigation_workflow import InvestigationWorkflow  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run V4 investigation workflow")
    parser.add_argument("--metric", default="fpd7")
    parser.add_argument("--analysis-date", default="2026-05-20")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    analysis = date.fromisoformat(args.analysis_date)
    result = InvestigationWorkflow.run(
        metric_name=args.metric,
        analysis_date=analysis,
    )

    if args.json:
        print(result.model_dump_json(indent=2))
        return

    print(f"status: {result.workflow_status}")
    print(f"needs_investigation: {result.needs_investigation}")
    print(f"executed_skills: {', '.join(result.executed_skills)}")
    if result.executive_summary:
        print(f"\nExecutive summary:\n{result.executive_summary}")
    if result.generated_report_path:
        print(f"\nReport: {result.generated_report_path}")
    if result.investigation_conclusion:
        print(f"\n{result.investigation_conclusion.business_summary}")


if __name__ == "__main__":
    main()
