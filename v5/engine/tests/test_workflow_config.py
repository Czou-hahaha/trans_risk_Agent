"""Config-driven workflow loader and router tests."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

_ENGINE = Path(__file__).resolve().parents[1]
_V1 = _ENGINE.parents[1] / "v1"
if str(_ENGINE) not in sys.path:
    sys.path.insert(0, str(_ENGINE))
if str(_V1) not in sys.path:
    sys.path.insert(0, str(_V1))

from workflow_config.loaders.workflow_config_loader import WorkflowConfigLoader
from workflow_config.schemas.workflow_config_schema import WorkflowRulesDocument
from workflow.workflow_router import WorkflowRouter
from workflow.workflow_rules import load_workflow_rule_config

from tests.test_investigation_workflow import _monitor, _trend


class TestWorkflowConfigLoader:
    def test_load_default_configs(self) -> None:
        cfg = WorkflowConfigLoader().load()
        assert cfg.skill_enabled("metric_monitor")
        assert cfg.skill_requires_trigger("trend_analysis", "anomaly_detected")
        assert cfg.skill_requires_trigger("strategy_impact", "deployment_detected")
        assert cfg.thresholds.contributor_concentration_pp == pytest.approx(0.35)

    def test_severity_maps_to_rule_config(self) -> None:
        rules = load_workflow_rule_config()
        assert rules.default_strategy_name == "RISK_003"
        assert rules.default_strategy_deployment == date(2026, 5, 10)


class TestConfigDrivenRouter:
    def test_anomaly_enables_trend_and_contribution(self) -> None:
        plan = WorkflowRouter().plan_initial(
            _monitor(), analysis_date=date(2026, 5, 20)
        )
        assert plan.run_trend_analysis
        assert plan.run_dimension_contribution
        assert "metric_anomaly" in plan.trigger_reasons

    def test_disable_trend_via_yaml(self, tmp_path: Path) -> None:
        configs = tmp_path / "configs"
        configs.mkdir()
        default_root = Path(__file__).resolve().parents[2].parent / "v1" / "workflow_config" / "configs"
        for name in (
            "workflow_rules.yaml",
            "skill_triggers.yaml",
            "severity_thresholds.yaml",
        ):
            text = (default_root / name).read_text(encoding="utf-8")
            if name == "workflow_rules.yaml":
                text = text.replace(
                    "trend_analysis:\n  enabled: true",
                    "trend_analysis:\n  enabled: false",
                )
            (configs / name).write_text(text, encoding="utf-8")

        plan = WorkflowRouter(config_root=str(configs)).plan_initial(
            _monitor(), analysis_date=date(2026, 5, 20)
        )
        assert not plan.run_trend_analysis
        assert plan.run_dimension_contribution

    def test_trend_deterioration_enables_segment(self) -> None:
        router = WorkflowRouter()
        plan = router.plan_initial(_monitor(), analysis_date=date(2026, 5, 20))
        plan = router.apply_trend(plan, _trend().trend_finding)
        assert plan.run_segment_stability
        assert "trend_deterioration" in plan.trigger_reasons
