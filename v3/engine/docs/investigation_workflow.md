# Investigation Workflow (V4)

Deterministic orchestration for the AI Risk Investigation Workspace — not a chatbot, LangChain flow, or multi-agent runtime.

## 1. Workflow Purpose

Compose analytics skills into an end-to-end investigation:

```text
User goal + metric + analysis_date
  → InvestigationWorkflow (routing + sequencing)
  → findings protocol aggregation
  → InvestigationReportBuilder (deterministic narrative)
  → workspace UI (timeline + findings + report)
```

## 2. Workflow Routing

`WorkflowRouter` (`workflow/workflow_router.py`) applies rules from `workflow_rules.py`:

| Signal | Skill |
|--------|--------|
| `metric_monitor.needs_investigation` | `trend_analysis`, `dimension_contribution` |
| Upward / deteriorating trend | `segment_stability` |
| Top contributor concentration | reinforces contribution |
| Strategy deployment near `analysis_date` | `strategy_impact` |
| Always (when contributors exist) | `finding_summary` |
| Always | `report_builder` |

Skipped skills (missing DB data) record `skipped` on the timeline without failing the run.

## 3. Investigation Context

`InvestigationContext` (`workflow/investigation_context.py`) holds:

- `investigation_id`, `metric_name`, `analysis_date`, `trigger_reason`
- `executed_skills`, `findings`, `timeline`, `risk_summary`
- Typed results: monitor, trend, contribution, segment stability, strategy impact, conclusion
- `executive_summary`, `generated_report_path`

## 4. Timeline System

`InvestigationTimelineEvent` (`models/investigation_timeline.py`):

- `timestamp`, `skill_name`, `execution_status`, `summary`, `duration_ms`, `step_order`

Persisted to `investigation_steps` by the backend service.

## 5. Findings Aggregation

Each completed skill appends a JSON finding to `context.findings` via the unified `BaseFinding` protocol.

## 6. Report Generation

`InvestigationReportBuilder` (`report/investigation_report_builder.py`):

```text
structured findings → section summarization → executive synthesis → markdown
```

Output: `engine/reports/investigation_{id}.md`

Sections: Executive Summary, Trend Analysis, Key Contributors, Segment Stability, Strategy Impact, Risk Recommendations.

## 7. Frontend Workspace

- `POST /api/investigation/run` — start investigation
- `GET /api/investigation/{id}` — detail + timeline steps
- `GET /api/investigation/{id}/report` — markdown report payload

UI: `frontend/app/investigation/` — timeline (left), findings (center), evidence charts (right), report preview (bottom).

## 8. Future Extensions

- Async workers (Celery) for long-running investigations
- Optional LLM narrative enhancement layer on top of deterministic report
- Per-channel strategy metadata and deployment registry
- Workflow version pinning and replay

## Entrypoint

```python
from workflow.investigation_workflow import InvestigationWorkflow

result = InvestigationWorkflow.run(
    metric_name="fpd7",
    analysis_date="2026-05-20",
)
```
