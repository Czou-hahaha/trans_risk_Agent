---
name: overseas_cashloan_kpi_definitions
description: |
  海外现金贷 KPI 口径：产品形态、通过率、FPD、period2~8、定价公式。
  只定义「算什么」，不负责异动门控与维度 SQL。
  当用户问指标怎么算、FPD7 口径、period2 含义时使用。
---

# overseas_cashloan_kpi_definitions

**职责**：海外现金贷业务的**指标口径、计算公式、产品形态与市场语境**（只做定义，不做取数、不做异动判定）

**计算实现**：`v1/skill_runtime/` + `v1/models/metric_profiles.py`（聚合口径枚举与 profile）

**后置**：`metric_monitor_skill.md` 负责「变化是否够大、要不要查」

---

## 1. Skill Purpose

本 skill **只回答三件事**：

1. 我们做的**是什么生意**、唯一目标是什么；  
2. **产品形态**（15 天一期、2～8 期）如何影响指标含义；  
3. **每个核心指标**的分子分母、样本口径、在代码里怎么算。

**不包含**（交给其他 skill）：

| 主题 | 负责 skill |
|------|------------|
| PKL / 数仓取数 | 数据层或 `metric_monitor` 的 repository |
| \|Δ\|≥2pp 是否查案 | `metric_monitor_skill` |
| 维度归因 | `dimension_contribution_skill` |

---

## 2. 业务目标：赚钱

海外现金贷的经营逻辑可压缩为：

```text
利润 ≈ 放款规模 × 资产收益率 − 信用损失 − 获客/运营成本
```

| 杠杆 | 对应指标族 | 方向（粗略） |
|------|------------|--------------|
| **做大入口** | 申请量、订单通过率、金额通过率 | 通过率↑ → 规模↑（需盯风险） |
| **卖贵** | 新资产定价、通过件定价 | 定价↑ → 收入↑（需盯转化与逾期） |
| **控损** | 短期/长期、金额/订单风险率 | 逾期率↓ → 损失↓ |
| **久期与结构** | 平均放款期数 `floan_period`、期数 2～8 | 期限结构影响现金流与风险暴露 |

**分析时的统一原则**：

- 通过率变好但 FPD7 变差 → 可能是「放量牺牲质量」，未必真赚钱；  
- FPD7 变好但通过率大跌 → 可能是「收紧过度」，规模受损；  
- 长期风险（period2～8）与短期 FPD 背离 → 产品形态（多期）下的结构问题。

本 skill 定义的指标，是为上述利润拆解服务的**标准度量**，不是为报表堆砌。

---

## 3. 产品形态（海外现金贷）

| 项 | 定义 |
|----|------|
| 业务 | **海外现金贷**（单笔短久期、分期偿还） |
| 期次长度 | **15 天为一期**（`floan_period` 字段刻画总期数/期限结构） |
| 常见期数 | 一般从 **第 2 期** 起观测长期风险，最长到 **第 8 期**（`period2` … `period8`） |
| 第 1 期表现 | 用 **FPD1 / FPD3 / FPD7**（首逾类）刻画「短期」风险 |
| 数据粒度 | 订单级明细；时间锚点为 **`apply_date`（申请日）** |

**期数与指标映射（代码约定）**：

| 业务说法 | 指标键 | PKL 列族 |
|----------|--------|----------|
| 短期（首逾） | `fpd1` / `fpd3` / `fpd7` | `if_fpd{p}_overdue_amt/show_amt`, `if_fpd{p}_overdue/show` |
| 第 2～8 期（15 天×期） | `period2` … `period8` | `period{N}_dpd7_overdue_amt/show_amt`, `period{N}_dpd7_overdue/show` |

> `mob1` / `mob2` 用于部分趋势模块，**不在**默认 `LONG_SHORT_RISK_KEYS` 热力图列表中（见 `models/metric_profiles.py`）。

---

## 4. 市场与用户结构（分析维度）

海外现金贷的「市场」在数据上体现为**客群与渠道结构**，用于解释指标异动，而非本 skill 去拉外部宏观数据。

常用拆分维度（`FILTER_DIMS`，见 `models/metric_profiles.py`）：

| 维度字段 | 典型用途 |
|----------|----------|
| `order_tag` | 渠道 / 流量来源 |
| `risk_level` | 风险等级分层 |
| `cus_type` | 新客 / 老客等 |
| `shouxin_apr_bin` | 授信定价带 |
| `credit_amount_bin` | 额度带 |
| `mob_bin` | MOB 切片 |
| `loan_status` | 贷款状态 |
| `freloan_num` | 复借次数等 |
| `floan_period` | **期限结构（与 15 天×期数直接相关）** |

分析时默认：**先看全局 KPI 异动，再按上表维度做归因**（`dimension_contribution_skill`）。

### 4.1 用户状态类维度的解读边界

下列字段常用于描述客群，但**不等于**可因果归因的 driver：

- `cus_type`（新客 / 老客）
- `mob_bin`、年龄或年龄段分箱
- 其它「标签几乎不变」的 cohort 字段

**规则**（与 `dimension_contribution_skill.md` §2.1 一致）：

- 若某周期内该字段 **100% 或 ≥98% 为同一标签** → 表示**当前样本只有这一类用户**，禁止在报告中写「指标变好/变坏是因为老客/新客」；
- 只有该维度在 current / previous **均存在多个有效 segment**（各自占比 < 98%）时，才可把某一取值列为贡献 driver。

---

## 5. 核心指标目录

以下公式来自历史 `metrics_core` 模块（逻辑已收敛到 `models/metric_profiles.py` 与灌库脚本）。  
除特别说明外，比率为 **0～1 小数**（展示时 ×100 为 %）。

### 5.1 规模与转化（赚钱入口）

| 指标名 | 中文 | 计算公式 | 样本口径 |
|--------|------|----------|----------|
| `n_apply_order` | 申请订单数 | `count(fcash_order_no)` 或行数 | 时间桶内全部申请 |
| `order_pass_rate` | **订单通过率** | `Σ 1{if_pass=1} / n_apply_order` | 桶内全部申请 |
| `amt_pass_rate` | **金额通过率** | `Σ ftotal_principal / Σ fapply_amount` | 桶内全部申请 |
| `sum_pass_order` | 通过订单数 | `Σ 1{if_pass=1}` | 同上 |
| `sum_fapply_amount` | 申请金额合计 | `Σ fapply_amount` | 同上 |
| `sum_ftotal_principal` | 通过本金合计 | `Σ ftotal_principal` | 同上 |

**Dashboard 周环比（通过率）**：

| 指标名 | 计算公式 | 时间窗 |
|--------|----------|--------|
| `order_pass_rate_this_week` | 本周 `order_pass_rate` | 自然周（周一至周日） |
| `order_pass_rate_last_week` | 上周同上 | 再前 7 天 |
| `order_pass_rate_wow` | `(本周−上周)/上周` | 相对变化率 |

> **注意**：通过率用**全量申请**；与 FPD 的 `if_fpd7_show=1` 子集不同，对比窗口也不同（自然周 vs 14 天 cohort）。

---

### 5.2 短期风险（FPD1 / FPD3 / FPD7）

| 指标名 | 中文 | 计算公式 | 样本口径 |
|--------|------|----------|----------|
| `fpd{p}_amt_overdue_rate` | **短期金额风险** | `Σ oa / Σ sa` | 桶内全部行 |
| `fpd{p}_order_overdue_rate` | **短期订单风险** | `Σ oo / Σ ss` | 同上 |
| `fpd{p}_order_confidence` | 短期表现期覆盖率 | `Σ ss / sum_pass_order` | 分母为**通过订单数** |

**Investigation FPD7 金额口径（更严）**：

| 指标名 | 计算公式 | 样本口径 | 时间窗 |
|--------|----------|----------|--------|
| `fpd7_amt_overdue_rate_current_2w` | `Σ if_fpd7_overdue_amt / Σ if_fpd7_show_amt` | **`if_fpd7_show = 1`** | 近 14 自然日 |
| `fpd7_amt_overdue_rate_prior_2w` | 同上 | 同上 | 锚定日前 14 日 |
| `fpd7_delta_pp` | `(current−prior)×100` | 同上 | — |

---

### 5.3 长期风险（第 2～8 期，15 天×期）

| 指标名 | 中文 | 计算公式 |
|--------|------|----------|
| `{key}_amt_overdue_rate` | **长期金额风险** | `Σ overdue_amt / Σ show_amt` |
| `{key}_order_overdue_rate` | **长期订单风险** | `Σ overdue / Σ show` |

`key ∈ {period2,…,period8}`（及热力图中的 `fpd7`）。

---

### 5.4 定价与期限（单位经济）

| 指标名 | 中文 | 计算公式 | 样本 |
|--------|------|----------|------|
| `new_asset_pricing` | 新资产定价（粗） | `Σ ftotal_interest / Σ ftotal_principal` | 桶内全部订单 |
| `avg_pass_order_pricing` | 通过件平均定价 | `mean(ftotal_interest/ftotal_principal)` on passed | `if_pass=1` |
| `avg_floan_period_pass` | 通过件平均放款期数 | `mean(floan_period)` on passed | `if_pass=1` |

---

### 5.5 指标族对照

| 你的说法 | 本 skill 指标键 | 类型 |
|----------|-----------------|------|
| 订单通过率 | `order_pass_rate` | 转化 |
| 金额通过率 | `amt_pass_rate` | 转化 |
| 短期订单风险 | `fpd1/3/7_order_overdue_rate` | 短期 |
| 短期金额风险 | `fpd1/3/7_amt_overdue_rate` | 短期 |
| 长期订单风险 | `period2..8_order_overdue_rate` | 长期 |
| 长期金额风险 | `period2..8_amt_overdue_rate` | 长期 |

**异动监控**（`metric_monitor_skill`）应对上表**所有你关心的 KPI** 配置 `metric_name`；当前 demo 库种子了 `fpd7`、`approval_rate`（正式应对齐 `order_pass_rate`）。

---

## 6. 口径铁律（算错必查）

| # | 规则 |
|---|------|
| 1 | 金额风险一律 **sum 分子 / sum 分母**，禁止对日率简单平均（除非 monitor 显式约定日均） |
| 2 | FPD7 Investigation **必须** `if_fpd7_show=1` |
| 3 | FPD7 双周窗锚在 **show=1 子集最新申请日**，不是全表 max 日 |
| 4 | 通过率周环比用 **自然周 + 全量申请** |
| 5 | 长期风险 period2～8 与 FPD7 列族不同，勿混用 `if_fpd7_*` 算 period3 |
| 6 | `floan_period` 矩阵分析排除取值 10 |

---

## 7. 与 Workflow 其他 skill 的边界

```text
overseas_cashloan_kpi_definitions   ← 本文：算什么、怎么算
        ↓
metric_monitor_skill              ← |Δ| 门控、是否发起归因
        ↓
dimension_contribution_skill      ← 按 FILTER_DIMS 归因
        ↓
finding_summary_skill             ← 调查结论
```

---

## 8. 待核对 / 已知待办

| 项 | 说明 |
|----|------|
| `approval_rate` vs `order_pass_rate` | demo 种子用 `approval_rate`；**正式口径应为 `order_pass_rate`** |
| PKL 旧函数 `compute_fpd7` | 与金额口径可能不一致；**以 `metric_profiles` + 灌库脚本为准** |
| 外部宏观市场数据 | 本 skill 不定义；若需行业大盘需另建 market research skill |

---

## Appendix：实现索引

| 模块 | 作用 |
|------|------|
| `models/metric_profiles.py` | 指标 profile、FILTER_DIMS、门控类型 |
| `tools/` 灌库脚本 | PKL → `metrics_daily` / `metric_breakdowns` |
| `skill_runtime/metric_monitor.py` | 双周期监控 |

> 历史 `v1/backend/app/services/metrics_core.py` 已移除；口径以本 skill + `models/` 为准。
