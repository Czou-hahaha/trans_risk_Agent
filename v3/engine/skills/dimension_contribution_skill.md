---
name: dimension_contribution
description: |
  结构化维度归因：volume-weighted contribution_pp，跨维度 Top N。
  前置 metric_monitor 门控。输出 ContributionFinding。
  当需要「谁拉高了 FPD7」「渠道/客群贡献度」时使用。
---

# dimension_contribution_skill

**Python 实现**：`v1/skill_runtime/dimension_contribution.py` · 引擎：`v1/tools/engines/contribution_engine.py` · DB：`v1/tools/db/contribution/`

**Upstream**：`metric_monitor_skill.md`（门控 + `attribution_hint`）

**KPI Definitions**：`overseas_cashloan_kpi_definitions.md`

**Status**：Production-ready（deterministic，无 LLM）

---

## 1. Skill Purpose

`dimension_contribution_skill` 是 **AI Risk Investigation Workflow** 的**核心 intelligence layer**（路线图 **[D] 维度归因**）。

在 `metric_monitor_skill` 按指标类型判定需要调查（短期 \|Δ\|≥1pp、通过率 ≥2pp、长期 ≥2pp 等，见 `metric_monitor_skill.md` §3.1）之后，本 skill 回答：

> **到底是哪个维度、哪个取值，导致组合层指标恶化或改善？**

本 skill **只负责**：

- 从 `metric_breakdowns` 读取按维度拆分的日度明细；
- 对 current / previous 周期做**样本量加权聚合**；
- 用**确定性公式**计算 `delta_pp` 与 `contribution_pp`；
- 跨维度全局排序，输出 Top N 可解释 `ContributionFinding`。

**不负责**：LLM 推理、SQL 自动生成、Agent 编排、报告渲染、Dashboard。

---

## 2. Business Context

| 场景 | 典型指标 | 分析问题 |
|------|----------|----------|
| 风险恶化 | FPD7、长期 roll 风险 | 哪个 channel / score_band 拉高组合 FPD？ |
| 通过率波动 | approval_rate | 哪个渠道通过率掉最多？ |
| 量级异常 | volume | 哪个 segment 贡献主要增量/缩量？ |
| 风险改善 | FPD7 下降 | 改善主要来自哪里？是否可持续？ |

与 chatbot 式「生成 SQL」不同，本 skill 提供**稳定、可复现、可审计**的归因数字，供下游 `finding_summary` 与人工复核使用。

---

## 2.1 维度可归因性（必须遵守）

**用户状态 / 客群类字段**（如 `cus_type` 新老客、`mob_bin`、年龄分箱等）若在某一分析周期内 **全部为同一取值，或单一取值样本量占比 ≥ 98%**，通常表示：

> 当前窗口内**只有这一类用户**（样本构成），而不是「这一类用户把组合指标拉高/拉低了」。

因此：

| 情况 | 处理方式 | 报告里怎么说 |
|------|----------|----------------|
| 当前或对比周期内，该维度 **≥98% 为同一取值** | **整维剔除**，不参与 Top N、不进 LLM | 不写「风险因老客下降/上升」 |
| 某 segment 在当前周期 `volume_share ≥ 98%` | **该 segment 剔除** | 不写该取值为 primary driver |
| 渠道、期数、风险档等多值且分散 | 正常算 `contribution_pp` | 可写「率变 + 占比」 |

实现常量：`workflow/constants.py` → `DIMENSION_DOMINANCE_THRESHOLD = 0.98`；逻辑在 `contribution_engine.is_attributable_period` / `filter_attributable_contributors`。

**禁止的错误叙事**（示例）：

- 「FPD7 改善主要来自 `cus_type=老客`」——当本周样本几乎全是老客时，这是**口径/样本边界**，不是老客这一客群带来的改善。
- 把 **100% 单客群的率差** 当成组合层 drivers（会与 portfolio delta 数值上「对齐」，但业务上无效）。

**正确叙事**：

- 组合层：`fpd7` 本周 vs 上周变化多少 pp；
- 可归因维度：在 **多 segment 并存** 的维度上，说明谁率变更大、谁占比更高（必要时拆成「率效应 / 结构效应」）。

---

## 3. Contribution Methodology

对每个 `dimension_name` 下的每个 `dimension_value`：

### 3.1 周期聚合（样本量加权）

```text
metric_rate = Σ(metric_value × sample_size) / Σ(sample_size)
volume_share = segment_volume / total_volume   # 分母为当前周期该维度下全体取值样本量之和
```

### 3.2 贡献度（核心公式）

```text
delta_pp          = (current_rate - previous_rate) × 100
contribution_pp   = (current_rate - previous_rate) × volume_share × 100
```

含义：该 segment 相对上周期的**率差**，按其在组合中的**当前周期体量占比**分摊到组合层变化（单位：百分点 pp）。

### 3.3 全局排序

- 对所有 `dimension_list` 中的维度、所有取值产生的 contributor **合并**；
- 按 `contribution_pp` **降序**（恶化场景下正值为拉高组合的主因）；
- 取 Top N。

> 与 `contribution_engine.py` 公式一致，便于单测与 PKL 灌库结果对照。

---

## 4. Inputs

`DimensionContributionSkill.run()`：

| 参数 | 类型 | 含义 |
|------|------|------|
| `metric_name` | `str` | 如 `fpd7`、`approval_rate`、`volume` |
| `current_period` | `PeriodRange` 或 `(start, end)` | 当前分析窗口（含首尾日） |
| `previous_period` | `PeriodRange` 或 `(start, end)` | 对比窗口 |
| `dimension_list` | `list[str]` | 如 `["channel","score_band","product","region"]` |
| `top_n` | `int` | 默认 5 |

也可用 `DimensionContributionInput` + `run_from_input()`。

数据前提：`metric_breakdowns` 已按 KPI 定义灌入（日粒度、`metric_value` 为小数率如 `0.028` = 2.8%）。

---

## 5. Outputs

`DimensionContributionResult`（Pydantic）：

```json
{
  "metric_name": "fpd7",
  "current_period_start": "2026-05-11",
  "current_period_end": "2026-05-17",
  "portfolio_delta_pp": 2.3,
  "top_contributors": [
    {
      "dimension_name": "channel",
      "dimension_value": "partner_X",
      "current_value": 4.1,
      "previous_value": 2.8,
      "delta_pp": 1.3,
      "contribution_pp": 0.45,
      "rank": 1,
      "severity": "high",
      "evidence": { "volume_share": 0.35, "current_volume": 24500 },
      "summary": "partner_X contributed +0.45pp to fpd7 increase ..."
    }
  ]
}
```

展示字段 `current_value` / `previous_value` 为**百分点**（×100），与 `delta_pp` / `contribution_pp` 单位一致。

---

## 6. Findings Schema

| 模型 | 字段 | 说明 |
|------|------|------|
| `ContributionFinding` | `dimension_name`, `dimension_value` | 定位 segment |
| | `current_value`, `previous_value` | 加权周期率（%） |
| | `delta_pp` | 段内率变化 |
| | `contribution_pp` | 对组合变化的贡献 |
| | `rank` | 全局排名 |
| | `severity` | `low` / `medium` / `high` |
| | `evidence` | 体量、占比、周期边界 |
| | `summary` | 一行可读结论 |
| `DimensionContributionResult` | `top_contributors` | 排序后的 findings 列表 |

---

## 7. Severity Rules

基于 **|contribution_pp|**：

| 区间 | severity |
|------|----------|
| < 0.1 pp | `low` |
| 0.1 ~ 0.3 pp | `medium` |
| > 0.3 pp | `high` |

常量见 `models/contribution.py`。

---

## 8. Failure Handling

| 异常 | 场景 | 行为 |
|------|------|------|
| `BreakdownDataNotFoundError` | 所有维度均无数据 | `run()` 抛错，Workflow 可降级为「无归因数据」 |
| `BreakdownQueryError` | DB 连接/SQL 失败 | 记录 error 日志并抛错 |
| 单维度无数据 | `analyze_dimension` 返回空列表 | 跳过该维度，其它维度继续 |
| 单维度 **≥98% 单值**（当前或对比周期） | 整维跳过，打 info 日志 | 不得进入 `top_contributors` |
| 全部维度均不可归因 | `BreakdownDataNotFoundError` | Workflow 降级为「无可归因 segment」 |

日志使用 `logging`，不打印密钥或完整 PII。

---

## 9. Future Extensions

| 方向 | 说明 |
|------|------|
| 数仓适配 | Repository 抽象为接口，实现 Hive / StarRocks 方言 |
| 交叉维度 | 两维组合 cube（channel × score_band） |
| 符号约定 | `risk_up_is_bad` 与 monitor 对齐，恶化/改善排序方向可配置 |
| Shapley / 回归分解 | 可选第二引擎，与当前 volume-weighted 并行 |
| Workflow 接入 | 读取 `MetricMonitorFinding.attribution_hint` 自动选维度集 |

**当前阶段明确不做**：LLM、Agent、tool calling、LangChain、自主 SQL、FastAPI、SSE、Dashboard。

---

## 10. Package Layout

```text
v1/
├── skill_runtime/dimension_contribution.py   # 编排入口
├── tools/engines/contribution_engine.py      # 核心算法
├── tools/db/contribution/                    # repository + models
├── models/contribution.py                    # Pydantic schemas
└── scripts/seed_metric_breakdowns.py
```

---

## 11. Quick Start

```bash
cd v1
pip install -r requirements.txt
cp .env.example .env   # PostgreSQL

python scripts/seed_metric_breakdowns.py
python scripts/run_investigation.py
```

---

## 12. Workflow Position

```text
overseas-cashloan-kpi-definitions
  → metric_monitor_skill          # 是否调查
  → dimension_contribution_skill  # 谁贡献了变化（本 skill）
  → finding_summary_skill         # 结构化结论
```
