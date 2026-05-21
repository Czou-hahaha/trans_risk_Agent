---
name: finding_summary
description: |
  将 monitor + contribution findings 合成为 InvestigationConclusion。
  风控调查解读层：用业务语言说明「数字意味着什么、该做什么」；数字由上游引擎算好，本层不重算。
  当需要「调查结论、业务总结、行动建议」时使用。
---

# finding_summary_skill

**Python 实现**：`v1/skill_runtime/finding_summary.py`

**Upstream**：`metric_monitor_skill.md`、`dimension_contribution_skill.md`

**Models**：`v1/models/`（`MetricMonitorFinding`、`ContributionFinding`、`InvestigationConclusion`）

**Status**：Production-ready (synthesis layer)

---

## 1. Skill Purpose

`finding_summary_skill` 将上游 **结构化 findings** 合成为 **investigation conclusion**：

```text
metric_monitor_skill        → MetricMonitorFinding
dimension_contribution_skill → ContributionFinding[]
finding_summary_skill         → InvestigationConclusion
```

回答：

> **这次风控调查的结论是什么？主要驱动因素对业务意味着什么？接下来该查什么、该做什么？**

### 分工：谁算数、谁解读

| 角色 | 谁来做 | 产出 |
|------|--------|------|
| **定量分析** | `metric_monitor` + `dimension_contribution`（确定性引擎） | 已审计的 `delta_pp`、`contribution_pp`、排名、门控 |
| **调查解读** | `finding_summary`（本 skill） | 业务摘要、风险假设、行动建议 |

非数据分析师要看报告，正是因为 **算数已在上面完成**；本 skill 的价值是 **把 findings 翻译成可决策的语言**，而不是让他们自己对着 JSON 猜含义。

本 skill **不重复做定量分析**（无 SQL、无聚合、不重算 delta/contribution、不重新排序）——不是「不会做分析」，而是 **分析结果已固定，避免 LLM 另算一套数导致与引擎不一致或幻觉**。

### 1.1 叙事约束（与 dimension_contribution 对齐）

上游已剔除 **单周期内 ≥98% 为同一取值的维度**（尤其新老客、MOB、年龄等用户状态字段）。合成结论时：

- **不得**把「样本里只有老客/只有新客」写成「风险因该客群改善/恶化」；
- **应当**优先引用渠道（`order_tag`）、风险档（`risk_level`）、期限（`floan_period`）等 **多 segment 并存** 的 driver；
- 若 Top contributors 很少或均为结构类维度，在 `business_summary` 中明确：**组合层变化已确认，可解释 segment 有限，需补数据或换窗口**。

`primary_driver` 格式：`dimension_name=dimension_value`（勿只写取值，避免歧义）。

---

## 2. Why LLM Is Introduced Here

| 层 | 职责 | 实现 |
|----|------|------|
| 引擎层 | 算对：波动、门控、贡献度、排名、可归因性过滤 | `metric_monitor` + `dimension_contribution` |
| 解读层 | 说清：组合变化含义、driver 业务解释、假设与动作 | `finding_summary`（LLM 可选） |

Workflow 中 **第一个使用 LLM 的环节**，承担的是 **资深风控调查员的叙述与判断表述**，不是第二个计算器。

引入 LLM 的原因：

- 业务读者需要 **连贯叙述**（率变 vs 量缩、多渠道叠加、证据不足时的留白），不是再看一张表；
- 数字与排序 **必须** 来自上游 JSON，LLM **引用并解释**，避免另算一套；
- LLM 不可用时，deterministic fallback 仍给出可读结论，workflow 不中断。

---

## 3. Deterministic vs Semantic Layer

```text
┌────────────────────────────────────────────┐
│  FindingSummarySkill                       │
│  · risk_direction (from attribution_hint)  │
│  · primary_driver / secondary_drivers      │
│  · confidence (formula)                    │
│  · LLM → business_summary / hypothesis     │
│  · fallback template if LLM fails          │
└────────────────────────────────────────────┘
         ▲                          ▲
         │ findings JSON            │ optional OpenAI-compatible API
         │                          │
  MetricMonitorFinding      ContributionFinding[]
```

**本层禁止**（保证与引擎一致、可审计）：

- 访问数据库 / 跑 SQL；
- 对 `delta_pp`、`contribution_pp`、率、排名 **做任何重算或改写**；
- 编造 payload 中不存在的维度、渠道、时间段或数字。

**本层必须**（这才是「要看数据」的理由）：

- 用 findings 中的数字说明 **组合层发生了什么**；
- 说明 **可归因 driver** 在业务上可能代表什么（渠道策略、测试收尾、结构收缩等）；
- 在证据不足时 **明确不确定性**，并给出可执行的下一步。

---

## 4. Inputs

| 输入                      | 来源                           | 说明                                                |
| ----------------------- | ---------------------------- | ------------------------------------------------- |
| `MetricMonitorFinding`  | `skill_runtime/metric_monitor` | 组合层波动、gate、severity、`delta_pp`、`attribution_hint` |
| `ContributionFinding[]` | `skill_runtime/dimension_contribution` | 已排序的 Top N 贡献者（`rank`, `contribution_pp`）         |

不重新定义 findings schema；直接消费 `models/` 子类型。

LLM 可见 payload 示例：

```json
{
  "metric_monitor": { "...": "..." },
  "top_contributors": [
    {
      "dimension_name": "channel",
      "dimension_value": "partner_X",
      "contribution_pp": 0.45,
      "rank": 1,
      "driver_label": "channel=partner_X"
    }
  ]
}
```

---

## 5. Outputs

`InvestigationConclusion`（`v1/models/conclusion.py`）：

| 字段                    | 来源                                                                  |
| --------------------- | ------------------------------------------------------------------- |
| `conclusion_id`       | UUID                                                                |
| `metric_name`         | metric monitor                                                      |
| `risk_direction`      | `deterioration` / `improvement` / `stable`（由 `attribution_hint` 映射） |
| `primary_driver`      | Top contributor，`dimension_name=dimension_value`                   |
| `secondary_drivers`   | 其余 contributor，同上格式                                            |
| `business_summary`    | LLM 或 fallback                                                      |
| `risk_hypothesis`     | LLM 或 fallback                                                      |
| `recommended_actions` | LLM 或 fallback                                                      |
| `confidence`          | deterministic 公式                                                    |
| `generated_at`        | UTC timestamp                                                       |

---

## 6. Prompt Design

实现：`v1/prompts/finding_summary.py` · LLM：`v1/services/llm.py`

System prompt 核心约束：

- 角色：**资深风控调查员**，向业务/策略方解读 **已算好的** findings；
- **可以且应当** 做数据分析意义上的 **解读**（率 vs 量、多 driver 叠加、与组合 delta 是否说得通）；
- **不得** 重算或改写任何数值；**不得** 编造未出现在 payload 中的事实；
- 不得将 **退化维度**（用户状态类且单值占比 ≥98%）描述为因果 driver；
- 输出 JSON：`business_summary`, `risk_hypothesis`, `recommended_actions`。

风格：内部调查报告（简洁、专业）；默认 **中文**，非闲聊。

---

## 7. Confidence Methodology

```python
confidence = min(
    1.0,
    abs(top_contributor.contribution_pp) / abs(portfolio_delta_pp),
)
```

含义：Top 贡献者对组合 `delta_pp` 的**解释程度**（0–1）。组合波动为 0 时，`confidence = 0`。

---

## 8. Failure Handling

| 场景                          | 行为                                  |
| --------------------------- | ----------------------------------- |
| 无 API Key / `USE_LLM=false` | 跳过 LLM，使用 fallback                  |
| LLM 返回非法 JSON               | 自动 **retry 1 次**                    |
| 仍失败 / API 异常                | `build_fallback_synthesis()` 模板结论   |
| `contributors` 为空           | 抛出 `ValueError`（workflow 不应在无归因时调用） |

Workflow **不会因 LLM 失败而崩溃**。

Fallback 示例：

```text
FPD7 increased by 2.30pp during the latest monitoring period.

The change was mainly driven by channel=partner_X, which contributed +0.45pp to the portfolio move.
```

---

## 9. LLM Service

实现：`v1/services/llm.py`

- OpenAI-compatible SDK（DeepSeek / OpenAI / Qwen 等）
- `response_format: json_object`
- Pydantic 校验 `LlmSynthesisResult`
- 无 LangChain / CrewAI / AutoGen

配置（`v1/.env`）：

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=
USE_LLM=true
```

---

## 10. Future Extensions

- Orchestrator 串联：`monitor → contribution → finding_summary → report`
- 多指标 investigation bundle（多个 `InvestigationConclusion`）
- 人工审核 gate（低 confidence 时标记「需复核」）
- 可选多语言模板（当前默认英文 investigation 文风）

---

## 11. Directory Layout

```text
v1/
├── skill_runtime/finding_summary.py
├── models/conclusion.py
├── prompts/finding_summary.py
├── services/llm.py
├── workflow/runner.py
└── scripts/run_investigation.py
```

---

## 12. Usage

```python
from skill_runtime.finding_summary import FindingSummarySkill

skill = FindingSummarySkill()
conclusion = skill.run(metric_monitor_finding, contribution_findings)
```

测试：

```bash
cd v1 && python scripts/run_investigation.py
```
