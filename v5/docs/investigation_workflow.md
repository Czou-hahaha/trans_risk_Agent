# Investigation Workflow (V4)

> 权威副本：`engine/docs/investigation_workflow.md`（内容与本文同步维护）

V4 确定性调查编排 — 详见 [MANIFEST.md](../MANIFEST.md) 文件清单。

## 入口

```python
from workflow.investigation_workflow import InvestigationWorkflow

result = InvestigationWorkflow.run(
    metric_name="fpd7",
    analysis_date="2026-05-20",
)
```

## 输出字段

- `workflow_status` — `completed` / `completed_no_issue` / `failed`
- `executed_skills` — 实际执行的 skill 列表
- `timeline` — `InvestigationTimelineEvent` 序列
- `executive_summary` — 确定性高管摘要
- `generated_report_path` — `engine/reports/investigation_{id}.md`

完整说明见 `engine/docs/investigation_workflow.md`。
