# Investigation Workflow (V4)

Full deterministic pipeline: `InvestigationWorkflow.run(metric_name, analysis_date)`.

See `docs/investigation_workflow.md` for routing, timeline, and report generation.

Legacy entry: `InvestigationWorkflowRunner` delegates to `InvestigationWorkflow`.

# Investigation Workflow (V3 legacy note)

## 1. Workflow Purpose

`InvestigationWorkflowRunner` 将三个 **deterministic skills** 串成一条可一键执行的风控调查流水线：

```text
metric_monitor → dimension_contribution → finding_summary
```

调用方只需提供指标名（例如 `metric_name="fpd7"`），即可得到结构化的 **`InvestigationResult`**，包含组合层监控结论、维度贡献列表与调查总结。

本模块是 **pipeline coordinator**，不承担 SQL、指标计算、贡献度算法或 LLM 推理； intelligence 留在各 `skill_runtime` 模块内。

**前置口径**：先读 `../skills/overseas_cashloan_kpi_definitions.md`。

---

## 2. Deterministic Orchestration Design

### 设计原则

| 原则 | 说明 |
|------|------|
| 固定阶段顺序 | 永远 monitor → contribution → summary，无动态路由 |
| 无 Agent / Planner | 不引入 LangChain、CrewAI、tool routing、reasoning loop |
| Gate 在 monitor | `needs_investigation == False` 时立即结束，不跑后续阶段 |
| 状态可追踪 | `WorkflowContext` 持久化各阶段产物与失败信息 |
| 边界清晰 | workflow 只编排，不修改 finding 字段、不重算指标 |

### 架构位置

```text
skills/*.md（4 个规范文档）
        ↓
models/（MetricMonitorFinding · ContributionFinding · InvestigationConclusion）
        ↓
skill_runtime（metric_monitor → dimension_contribution → finding_summary）
        ↓
workflow/runner.py  ← 本目录
        ↓
InvestigationResult
```

---

## 3. Stage Definitions

### Stage 1 — Monitor (`run_monitor_stage`)

- 调用：`MetricMonitorSkill.run(...)`（`skill_runtime/metric_monitor.py`）
- 输入：指标名、当前/对比周期
- 输出：`MetricMonitorFinding`
- 若 `needs_investigation == False`：
  - `workflow_status = completed_no_issue`
  - 返回 `InvestigationResult`（无 contribution / conclusion）

### Stage 2 — Contribution (`run_contribution_stage`)

- 仅在 monitor 判定需要调查时执行
- 调用：`DimensionContributionSkill.run(...)`（`skill_runtime/dimension_contribution.py`）
- 输出：`ContributionFinding[]` → 写入 `context.contribution_findings`

### Stage 3 — Summary (`run_summary_stage`)

- 调用：`FindingSummarySkill.run(metric_monitor, contributors)`（`skill_runtime/finding_summary.py`）
- 输出：`InvestigationConclusion` → 写入 `context.investigation_conclusion`
- 最终：`workflow_status = completed`

---

## 4. Workflow Context

[`context.py`](context.py) 中的 `WorkflowContext` 在单次 run 内携带状态：

| 字段 | 说明 |
|------|------|
| `workflow_id` | 本次调查 UUID |
| `metric_name` | 指标名 |
| `current_period` / `previous_period` | `(start_date, end_date)` |
| `started_at` | 开始时间 |
| `workflow_status` | `WorkflowStatus` 枚举 |
| `monitor_finding` | Monitor 阶段产物 |
| `contribution_findings` | Contribution 阶段产物 |
| `investigation_conclusion` | Summary 阶段产物 |
| `error_message` / `failed_stage` | 失败时填充（`monitor` / `contribution` / `summary`） |

---

## 5. Workflow Result Schema

[`result.py`](result.py) 定义对外输出 `InvestigationResult`：

```json
{
  "workflow_id": "...",
  "metric_name": "fpd7",
  "workflow_status": "completed",
  "needs_investigation": true,
  "monitor_finding": { "...": "MetricMonitorFinding" },
  "contribution_findings": [ "... ContributionFinding ..." ],
  "investigation_conclusion": { "...": "InvestigationConclusion" },
  "generated_at": "2026-05-17T12:00:00Z"
}
```

`workflow_status` 取值见 [`status.py`](status.py)：

- `running` — 运行中（通常仅在内存态）
- `completed` — 完整跑完三阶段
- `completed_no_issue` — monitor 未触发调查
- `failed` — 任一步骤异常

---

## 6. Error Handling

任一步骤抛出未捕获异常时：

1. `context.workflow_status = failed`
2. `context.failed_stage` 设为当前阶段名
3. `context.error_message` 记录异常信息
4. `build_final_result()` 仍返回 `InvestigationResult`（可能含部分阶段数据）

日志使用 `[Workflow]` 前缀；**不**打印 API key、secrets 或 raw prompts。

---

## 7. Usage

```python
from workflow.runner import InvestigationWorkflowRunner

runner = InvestigationWorkflowRunner(metric_name="fpd7")
result = runner.run()

print(result.workflow_status, result.needs_investigation)
```

默认周期与 skill 验收一致（7 日窗口，参考日见 [`constants.py`](constants.py) 的 `REFERENCE_DATE`）。可通过 `current_period` / `previous_period` / `reference_date` 覆盖。

### 运行与验收

```bash
cd v1
python tools/seed/seed_from_pkl.py
python scripts/run_investigation.py

# 测试
python -m pytest tests/test_workflow.py -q
```

依赖已 seed 的 `risk_metric_monitor` 与 `risk_dimension_contribution` 数据库（见 `docker-compose.yml`）。

---

## 8. 模块文件

| 文件 | 职责 |
|------|------|
| `runner.py` | 三阶段编排入口 |
| `context.py` | 单次 run 状态 |
| `result.py` | `InvestigationResult` |
| `status.py` | `WorkflowStatus` 枚举 |
| `constants.py` | 默认维度、周期、参考日 |

---

## 9. Future Extensions（当前未实现）

- FastAPI / HTTP API
- Dashboard / SSE
- Multi-agent 编排
- 多指标 bundle、调度器

当前范围：**单机 deterministic investigation workflow**。
