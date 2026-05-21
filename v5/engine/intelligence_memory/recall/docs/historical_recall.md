# Historical Recall — Investigation Intelligence Layer

> **路径**：`v5/engine/intelligence_memory/recall/`

## 设计目标

在 **Findings Persistence** 之上提供跨 investigation 的确定性历史查询，支持：

- 历史 contributor 查询（含 recurring top contributors）
- 历史 strategy impact 查询
- 历史 recurring segment / unstable segment 追踪
- 历史 dimension deterioration 查询
- 相似 investigation 匹配（无 embedding）

**明确不做**：vector retrieval、semantic embeddings、chatbot memory、autonomous agent memory。

## 模块结构

| 组件 | 文件 | 职责 |
|------|------|------|
| `InvestigationRecallService` | `investigation_recall_service.py` | 对外 API |
| `RecurringContributorEngine` | `recurring_contributor_engine.py` | 识别窗口内多次进入 Top N 的 contributor |
| `HistoricalLookupEngine` | `historical_lookup_engine.py` | 按 metric / dimension / type / 日期过滤 |
| `RecallResult` | `schemas/recall_result.py` | 结构化返回（供后续前端） |
| `RecurringPattern` | `schemas/recurring_pattern.py` |  recurring 模式描述 |

## API

```python
from intelligence_memory.recall import DateRange, InvestigationRecallService

svc = InvestigationRecallService()

# 连续出现在 Top Contributors 的维度值（默认 30 天内 ≥3 次）
svc.get_recurring_contributors(window_days=30, min_occurrences=3)

# 某维度值的恶化历史（delta_pp < 0 或 summary 含 deterioration）
svc.get_historical_dimension_deterioration(
    "channel", "partner_X",
    metric_name="fpd7",
    date_range=DateRange(date(2026, 4, 1), date(2026, 5, 20)),
)

# strategy impact 历史（finding_type=strategy_impact, dimension strategy）
svc.get_strategy_history(strategy_name="RISK_003")

# 最近 investigation 快照
svc.get_recent_investigations(limit=20, metric_name="fpd7")

# 确定性相似度：共同 contributor / strategy / 恶化 metric / unstable segment
svc.find_similar_investigations("inv-current", limit=10, min_score=1.0)
```

## 输出结构 `RecallResult`

| 字段 | 说明 |
|------|------|
| `matched_investigations` | 匹配或相似的 investigation 列表 |
| `recurring_patterns` | Recurring contributor 模式 |
| `historical_frequency` | 计数 map（如 contributor → 出现次数） |
| `similarity_score` | 相似查询时的最高分 |
| `findings` | 明细 finding 行（lookup / deterioration / strategy） |
| `recent_investigations` | 最近快照列表 |

## Recurring Contributor 逻辑

1. 查询 `finding_type=dimension_contribution` 且在时间窗口内。
2. 每个 investigation 按 `|contribution_pp|` 取 Top N（默认 3）。
3. 若同一 `(dimension_name, dimension_value)` 在 ≥ `min_occurrences` 个 investigation 中出现，则标记为 recurring。

## Similarity 逻辑（确定性）

对目标 investigation 与历史 investigation 比较特征集合：

| 特征 | 权重 |
|------|------|
| 共同 contributor | 1.0 / 个 |
| 共同 strategy | 2.0 / 个 |
| 共同恶化 metric | 1.0 / 个 |
| 共同 unstable segment | 1.0 / 个 |

得分 ≥ `min_score` 的 investigation 按分数降序返回。

## 测试

`v5/engine/tests/test_historical_recall.py` — SQLite 内存库，覆盖 recurring、lookup、deterioration、strategy、similarity。

## Recurring Pattern Engine（上层）

在 recall 之上，`patterns/RecurringPatternEngine` 聚合五类确定性风险模式（contributor、segment、strategy side effect、approval-risk shift、volume-risk tradeoff）。见 `patterns/docs/recurring_patterns.md`。

## 前端

当前仅返回 JSON 可序列化的 `RecallResult`；UI 接入留待后续。
