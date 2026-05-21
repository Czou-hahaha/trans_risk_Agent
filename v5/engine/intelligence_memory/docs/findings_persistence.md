# Findings Persistence — Risk Intelligence Storage Layer

> **维护目录**：`v5/engine/intelligence_memory/`（V5 结构化调查记忆层）

## 设计目标

调查 workflow 产生的 findings 原先只存在于 **runtime memory**（`InvestigationContext.findings`）。V5 引入 **structured intelligence persistence**，在 workflow 完成后将 findings 写入 Postgres，支持：

- 跨 investigation 查询
- 历史 contributor 统计（`dimension_name` / `dimension_value` + `contribution_pp`）
- 历史 strategy impact 追踪（`finding_type=strategy_impact`）
- 历史 unstable segment 追踪（`finding_type=segment_stability`）

**明确不做**：vector DB、embeddings、semantic memory、RAG、LangChain memory。

## 存储设计

| 组件 | 路径 | 职责 |
|------|------|------|
| `FindingStorageService` | `storage/finding_storage_service.py` | 对外 API：写入 / 按 metric、dimension、investigation 查询 |
| `FindingRepository` | `repositories/finding_repository.py` | `stored_findings` CRUD |
| `InvestigationRepository` | `repositories/investigation_repository.py` | `investigation_snapshots` 元数据 |
| `finding_mapper` | `storage/finding_mapper.py` | 将 skill finding dict 规范为 `StoredFinding` |
| Session | `storage/session.py` | `risk_intelligence` 库连接与 `init_db()` |

数据库：`risk_intelligence`（环境变量 `INTELLIGENCE_DATABASE_URL`）。

## Schema 设计

### `stored_findings`

| 字段 | 说明 |
|------|------|
| `finding_id` | 与 findings protocol 一致 |
| `investigation_id` | 所属调查 |
| `metric_name` | 指标名 |
| `finding_type` | `metric_monitor` / `dimension_contribution` / … |
| `dimension_name` / `dimension_value` | 贡献维度或 segment / strategy |
| `summary` | 文本摘要 |
| `severity` | 主要来自 `metric_monitor` |
| `contribution_pp` / `delta_pp` | 归因与变化幅度 |
| `generated_at` | finding 生成时间 |

### `investigation_snapshots`

轻量调查快照，便于按 metric 列出历史 investigation 及 findings 数量。

DDL：`migrations/create_findings_tables.sql`。

## 持久化生命周期

```text
InvestigationWorkflow.execute()
  → skills append findings to ctx.findings (memory)
  → workflow completes (COMPLETED / COMPLETED_NO_ISSUE / FAILED)
  → _persist_findings()
  → FindingStorageService.persist_investigation_findings()
  → stored_findings + investigation_snapshots
```

失败调查也会持久化已收集的 findings（若有），便于事后分析。

## Workflow 集成

`v5/engine/workflow/investigation_workflow.py` 在 `_build_result()` 前调用 `_persist_findings()`。持久化失败仅记录日志，**不阻断** workflow 返回结果。

## 查询示例

```python
from intelligence_memory import FindingStorageService

svc = FindingStorageService()
by_metric = svc.get_findings_by_metric("fpd7")
by_dim = svc.get_findings_by_dimension("channel", "paid_search")
by_inv = svc.get_findings_by_investigation(investigation_id)
```

## Historical Recall（已实现）

跨 investigation 确定性查询见 `recall/docs/historical_recall.md` 与 `InvestigationRecallService`。

```python
from intelligence_memory.recall import InvestigationRecallService

recall = InvestigationRecallService()
recall.get_recurring_contributors()
recall.find_similar_investigations(investigation_id)
```

## Recurring Pattern Engine（已实现）

跨 investigation **风险模式**自动发现见 `patterns/docs/recurring_patterns.md` 与 `RecurringPatternEngine`。

```python
from intelligence_memory.patterns import RecurringPatternEngine

engine = RecurringPatternEngine()
patterns = engine.detect_all(metric_name="fpd7")
```

## 未来扩展（未实现）

- 后端 HTTP API 暴露 recall / pattern 结果
- 与 backend `investigations` 表外键关联
- 只读 REST：`GET /api/intelligence/findings?metric=fpd7`
- 数据保留策略与归档
