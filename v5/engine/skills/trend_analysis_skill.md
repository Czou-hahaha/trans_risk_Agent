---
name: trend_analysis
description: |
  确定性时序趋势分析：滚动均值、斜率、连续上涨、波动率、异常波峰。
  回答「短期波动还是持续恶化」「趋势是否已形成」。
  非预测、非 ML、非 Prophet/ARIMA。
---

# trend_analysis_skill

**Python 实现**：`skill_runtime/trend_analysis.py`  
**工具层**：`tools/engines/trend_engine.py` · `tools/repositories/trend_repository.py`  
**模型**：`models/trend.py`  
**数据**：`metrics_daily`（组合层）/ `metric_breakdowns`（维度筛选）

**Status**：可独立运行；尚未接入 `workflow/runner.py`

---

## 1. 技能目的

在 **metric_monitor** 与 **dimension_contribution** 之间，补充「最近一段时间」的趋势视角：

- 风险是短期波动还是持续恶化？
- 是否存在连续环比上涨？
- 趋势方向与强度如何？
- 波动率是否偏高？是否有异常波峰期？

```text
（规划）metric_monitor → trend_analysis → dimension_contribution → finding_summary
（当前）TrendAnalysisSkill.run(...) 独立调用
```

---

## 2. 方法论

```text
宽表/长表
  → TrendRepository（仅此处 SQL + 日/周聚合）
  → TrendEngine（纯算法）
  → TrendFinding + 中文确定性 summary
```

禁止：预测、Prophet、ARIMA、LSTM、ML pipeline、异常检测 Agent。

---

## 3. 滚动分析

| 日历窗口 | 日粒度 period 数 | 周粒度 period 数 |
|----------|------------------|------------------|
| 7d       | 7                | ~1 周            |
| 14d      | 14               | ~2 周            |
| 30d      | 30               | ~4–5 周          |

`rolling_change_pp`：最新短窗滚动均值 vs 基线滚动均值（百分点）。

---

## 4. 斜率

`calculate_linear_slope()`：对索引 0..n-1 最小二乘。

| 条件 | trend_direction |
|------|-----------------|
| slope > 阈值 | upward |
| slope < -阈值 | downward |
| 否则 | stable |

---

## 5. 波动率

- 标准差 + 变异系数 CV  
- `volatility_level`：low / medium / high（阈值 0.08 / 0.18）

---

## 6. 连续上涨与波峰

- `consecutive_up_periods`：从最近一期向前，严格递增的连续期数  
- `anomaly_periods`：留一法，当期 > 其余期均值 + 2σ（如 `2026-W15`）

---

## 7. Finding 字段

| 字段 | 说明 |
|------|------|
| trend_direction | upward / downward / stable |
| trend_strength | weak / moderate / strong |
| rolling_change_pp | 滚动变动（pp） |
| consecutive_up_periods | 连续上涨期数 |
| volatility_level | low / medium / high |
| summary | **中文**确定性摘要 |

---

## 8. 调用示例

```python
from tools.db.monitor.session import get_session
from tools.db.contribution.session import get_session as contrib_session
from skill_runtime.trend_analysis import TrendAnalysisSkill

with get_session() as mon, contrib_session() as con:
    r = TrendAnalysisSkill(mon, con).run(
        metric_name="fpd7",
        window_days=60,
        aggregation_level="week",
    )
    print(r.trend_finding.summary)
```

---

## 9. 后续扩展

- 接入 investigation workflow  
- 按 metric_profile 配置阈值  
- 维度切片趋势（channel / region 等）
