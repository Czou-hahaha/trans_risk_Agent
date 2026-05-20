# V1 vs V2 版本对比说明

> 供面试官、协作方快速理解：**V1 验证「调查引擎」，V2 验证「可演示的产品壳」**，业务语义一致。

---

## 1. 一句话总结

| 版本 | 一句话 |
|------|--------|
| **V1** | 把海外现金贷风控的 **监控 → 归因 → 结论** 做成 **可一键复现的 Python 流水线**。 |
| **V2** | 在 V1 引擎之上增加 **FastAPI + Next.js**，让调查过程 **可视化、可持久化、可给业务演示**。 |

---

## 2. 功能对比

| 能力 | V1 | V2 | 说明 |
|------|:--:|:--:|------|
| KPI 口径文档化 | ✅ | ✅ | `skills/overseas_cashloan_kpi_definitions.md` |
| 双周期指标监控 | ✅ | ✅ | `metric_monitor`，含 \|Δ\| 门控 |
| 维度贡献分析 | ✅ | ✅ | `dimension_contribution` |
| 调查结论生成 | ✅ | ✅ | `finding_summary`（规则 + LLM） |
| CLI 一键调查 | ✅ | ⚪ | `scripts/run_investigation.py` |
| Web Dashboard | ❌ | ✅ | KPI、最新调查、告警 |
| 发起调查（自然语言 goal） | ❌ | ✅ | 解析 metric 后跑 workflow |
| 步骤 Timeline + 轮询 | ❌ | ✅ | monitor → contribution → summary |
| 报告页 + Markdown 导出 | ❌ | ✅ | `investigation_reports` |
| 调查历史持久化 | ❌ | ✅ | `investigations` / `investigation_steps` |
| 多 Agent / 自主规划 | ❌ | ❌ | **两版均刻意不做** |
| LangGraph / RAG | ❌ | ❌ | 保持确定性主路径 |

---

## 3. 架构对比

### V1 架构

```text
skills/*.md（规范）
    → skill_runtime/（三阶段实现）
    → workflow/runner.py（固定顺序编排）
    → PostgreSQL（metrics_daily、metric_breakdowns）
    → CLI 输出 InvestigationResult
```

**特点**：最小可运行集；适合算法验证、单测、CI。

### V2 架构

```text
v2/engine/          # 与 V1 同构的 workflow + skill_runtime
v2/backend/         # FastAPI
    → investigation_service 调用 InvestigationWorkflowRunner
    → 每阶段写入 investigation_steps
    → 完成后写入 investigation_reports
v2/frontend/        # Next.js
    → Dashboard / Investigation / Report 页面
```

**特点**：引擎与 UI 解耦；换前端不影响归因逻辑。

---

## 4. 数据与存储对比

| 数据 | V1 | V2 |
|------|----|----|
| 日度指标 `metrics_daily` | ✅ | ✅（engine seed） |
| 维度明细 `metric_breakdowns` | ✅ | ✅ |
| 调查任务表 | ❌ | ✅ `investigations` |
| 阶段输出表 | ❌ | ✅ `investigation_steps` |
| 报告 JSON | ❌ | ✅ `investigation_reports` |

V2 **不替代** V1 的指标库设计，而是 **叠加** 调查过程态。

---

## 5. 从 V1 到 V2 的演进动机

| 痛点（V1） | V2 如何解决 |
|------------|-------------|
| 只有终端 JSON，业务方难理解 | Timeline + 分步详情页 |
| 每次调查无历史 | PostgreSQL 持久化 + Dashboard |
| 演示成本高 | `start-all.sh` 一键起前后端 |
| 无法从「一句话 goal」发起 | `goal_parser` + `POST /api/investigations` |

**未在 V2 解决的问题**（留给 V3+）：

- 跨指标趋势分析（V3 `trend_analysis` 本地开发中）
- 多案件并行调度、权限、审批流等企业特性

---

## 6. 代码复用关系

```text
v1/workflow/runner.py
v1/skill_runtime/*
v1/models/*
        │
        │  （V2 拷贝/同步到 v2/engine/）
        ▼
v2/engine/workflow/
v2/engine/skill_runtime/
v2/backend/app/services/investigation_service.py  # import runner
```

面试时可说明：**V2 不是重写业务，而是「引擎拷贝 + 服务层包装」**，降低回归风险。

---

## 7. 运行方式对比

| 项目 | V1 | V2 |
|------|----|----|
| 依赖安装 | `pip install -r v1/requirements.txt` | engine + backend requirements + `npm install` |
| 数据库 | `docker compose`（5433） | 同左 + `risk_investigation` 库 |
| 启动 | `python scripts/run_investigation.py` | `./scripts/start-all.sh` |
| 默认端口 | — | 前端 8000 / API 8001 |

---

## 8. 测试与质量

| 类型 | V1 | V2 |
|------|----|----|
| Workflow 集成 | `tests/test_workflow.py` | `engine/tests/test_workflow.py` |
| 维度覆盖 | `tests/test_dimension_coverage.py` | 同路径在 engine |
| API E2E | — | 可手工走 `/investigation/new` |

---

## 9. 选型建议（给面试官）

- 想看 **算法与风控逻辑**：clone **`V1-version`**，读 `skills/` + `workflow/README.md`。
- 想看 **全栈与产品化**：clone **`V2-version`**，跑控制台 + 看 `backend/app/services/investigation_service.py`。
- 想看 **版本演进思路**：读本文件 + 根目录 `README.md`。

---

## 10. 后续路线图（仓库外 / 本地 V3）

| 版本 | 状态 | 方向 |
|------|------|------|
| V1 | ✅ 已推送 `V1-version` | 确定性三阶段流水线 |
| V2 | ✅ 已推送 `V2-version` | 可视化 + 持久化 |
| V3 | 本地开发 | `trend_analysis` 趋势模块、前端 Dashboard 对齐 |
