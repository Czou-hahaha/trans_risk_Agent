# V5 全流程文件清单

本目录包含**跑通 Investigation 全流程**所需文件（自 `v4/` 复制；V5 增加 findings 持久化）。

## 1. V5 Intelligence Memory（findings 持久化）

| 路径 | 说明 |
|------|------|
| `engine/intelligence_memory/storage/finding_storage_service.py` | `FindingStorageService` API |
| `engine/intelligence_memory/repositories/` | finding / investigation repos |
| `engine/intelligence_memory/migrations/create_findings_tables.sql` | DDL |
| `engine/intelligence_memory/docs/findings_persistence.md` | 设计文档 |
| `engine/tests/test_findings_persistence.py` | 单元测试 |

## 2. Workflow 编排层（V5 核心）

| 文件 | 职责 |
|------|------|
| `engine/workflow/investigation_workflow.py` | `InvestigationWorkflow` 主编排 |
| `engine/workflow/workflow_router.py` | 确定性 skill 路由 |
| `engine/workflow/workflow_rules.py` | 路由阈值与策略日期规则 |
| `engine/workflow/investigation_context.py` | 调查上下文 |
| `engine/workflow/investigation_state.py` | 状态枚举 |
| `engine/workflow/result.py` | `InvestigationResult` 输出 |
| `engine/workflow/periods.py` | 分析窗口计算 |
| `engine/workflow/runner.py` | 兼容门面 |
| `engine/workflow/orchestrator/__init__.py` | 编排入口别名 |

## 2. Report 系统

| 文件 | 职责 |
|------|------|
| `engine/report/investigation_report_builder.py` | findings → 确定性报告 |
| `engine/report/report_sections.py` | 章节结构 |
| `engine/report/markdown_renderer.py` | Markdown 渲染 |
| `engine/reports/` | 生成的 `investigation_{id}.md` |

## 3. Analytics Skills（skill_runtime + tools）

| Skill | 编排 | 引擎 | 仓储 |
|-------|------|------|------|
| metric_monitor | `skill_runtime/metric_monitor.py` | `metric_monitor_logic.py` | `metrics_repository.py` |
| trend_analysis | `skill_runtime/trend_analysis.py` | `trend_engine.py` | `trend_repository.py` |
| dimension_contribution | `skill_runtime/dimension_contribution.py` | `contribution_engine.py` | `breakdown_repository.py` |
| segment_stability | `skill_runtime/segment_stability.py` | `stability_engine.py` | `segment_stability_repository.py` |
| strategy_impact | `skill_runtime/strategy_impact.py` | `strategy_impact_engine.py` | `strategy_impact_repository.py` |
| finding_summary | `skill_runtime/finding_summary.py` | — | `services/llm.py` |

## 4. 数据模型

`engine/models/` — `base_finding`, `metric_monitor`, `contribution`, `trend`, `segment_stability`, `strategy_impact`, `investigation_timeline`, `conclusion`, …

## 5. 数据库

| 组件 | 路径 |
|------|------|
| Monitor ORM | `tools/db/monitor/` |
| Contribution ORM | `tools/db/contribution/` |
| Strategy 表 | `tools/db/monitor/models/strategy_metrics_daily.py` |
| Seed | `tools/seed/seed_from_pkl.py` |
| Docker 初始化 | `docker/init-databases.sql` |

## 6. Backend（持久化 + API）

| 文件 | 职责 |
|------|------|
| `backend/app/services/investigation_service.py` | V4 步骤持久化 |
| `backend/app/api/investigation.py` | `/api/investigation/*` |
| `backend/app/api/investigations.py` | 列表 / dashboard |
| `backend/app/services/report_builder.py` | 报告 API |
| `backend/app/db/models.py` | `investigations` + steps + reports |

## 7. Frontend（Workspace）

| 路径 | 职责 |
|------|------|
| `frontend/app/investigation/page.tsx` | 启动调查 |
| `frontend/app/investigation/[id]/page.tsx` | 三栏 Workspace |
| `frontend/components/investigation/*` | Timeline / Findings / Charts / Report |

## 8. 测试

| 文件 | 覆盖 |
|------|------|
| `engine/tests/test_investigation_workflow.py` | 全流程 mock、路由、报告 |
| `engine/tests/test_workflow.py` | 兼容 runner |
| `engine/tests/test_*_engine.py` | 各 skill 引擎 |

## 9. 启动脚本

- `scripts/start-all.sh`
- `scripts/start-backend.sh`
- `engine/scripts/run_investigation.py`
