# Investigation Evaluation System

> **路径**：`v5/engine/evaluation/`

## 目标

对 investigation workflow 建立 **确定性 evaluation layer**（无 LLM / embeddings / AI eval 框架），评估：

| 维度 | `evaluation_type` | Evaluator |
|------|-------------------|-----------|
| Finding 质量 | `finding_quality` | `FindingEvaluator` |
| Workflow 一致性 | `workflow_consistency` | `WorkflowEvaluator` |
| Report 完整性 | `report_completeness` | `ReportEvaluator` |
| Pattern 置信度 | `pattern_confidence` | `PatternEvaluator` |

## 输出

### `EvaluationResult`

- `evaluation_type`
- `evaluation_score` (0–1)
- `detected_issues`
- `recommendations`
- `generated_at`

### `EvaluationMetrics`（Dashboard）

- `workflow_quality`
- `report_quality`
- `finding_confidence`
- `pattern_confidence`
- `overall_score`

## 使用

```python
from evaluation import EvaluationService
from workflow.result import InvestigationResult

svc = EvaluationService()
bundle = svc.evaluate_investigation(result)
print(bundle.metrics.overall_score)
```

从持久化 report JSON：

```python
bundle = svc.evaluate_from_payload(report_json)
```

## API

`GET /api/investigations/{id}/evaluation` — 基于 `InvestigationReport.report_json` 运行评估。

## 前端

Investigation 详情页 **Investigation Quality Panel** 展示四维质量分数与 issues。

## 测试

`v5/engine/tests/test_evaluation_system.py`
