---
name: segment_stability
description: |
  确定性 segment 风险结构稳定性分析：波动性、稳定性评分、趋势、regime shift、连续恶化。
  回答「哪些 segment/渠道风险结构不稳定」「是长期稳定还是最近突然异常」。
  非预测、非 ML、非异常检测 Agent。
---

# segment_stability_skill

**Python 实现**：`skill_runtime/segment_stability.py`  
**工具层**：`tools/engines/stability_engine.py` · `tools/repositories/segment_stability_repository.py`  
**模型**：`models/segment_stability.py`  
**数据**：`metric_breakdowns`（按 dimension_name / dimension_value 长表）

**Status**：可独立运行；尚未接入 `workflow/runner.py`

---

## 1. Skill Purpose

在 **dimension_contribution** 之后补充「时间维度」视角：

- 哪个 segment 贡献了变化？（contribution 已回答）
- 该 segment 是长期稳定还是最近突然恶化？（本 skill）

```text
（规划）metric_monitor → trend_analysis → dimension_contribution → segment_stability → finding_summary
（当前）SegmentStabilitySkill.run(...) 独立调用
```

---

## 2. Stability Methodology

```text
metric_breakdowns（宽表字段：event_date, metric_value, sample_size, dimension_*）
  → SegmentStabilityRepository（仅此处 SQL + 日/周聚合）
  → StabilityEngine（纯算法，逐 segment）
  → SegmentStabilityFinding + 中文确定性 summary
  → 按不稳定程度排序取 top_n
```

禁止：预测、Prophet、ARIMA、LSTM、ML pipeline、向量库、LLM 摘要。

---

## 3. Volatility Analysis

对每个 segment 时间序列计算：

| 指标 | 说明 |
|------|------|
| std | 全序列总体标准差 |
| rolling_std | 滚动窗口标准差（末期为当前波动） |
| coefficient_of_variation (CV) | \|std / mean\| |

`volatility_level`（基于 CV）：

| CV | level |
|----|-------|
| < 0.08 | low |
| < 0.18 | medium |
| ≥ 0.18 | high |

`stability_score`：\( \max(0, 1 - \text{CV} / (2 \times cv\_high)) \)，范围 0~1，越高越稳定。

---

## 4. Regime Shift Detection

将序列分为：

- **近期窗口**：默认最近 14 天对应周数（或序列长度 25% 至少 2 期）
- **历史窗口**：其余各期

判定：

```text
recent_mean - historical_mean > regime_shift_rate_threshold (默认 0.005)
且 recent_mean > historical_mean
→ regime_shift_detected = true
```

用于识别「过去长期稳定、最近突然恶化」。

---

## 5. Consecutive Deterioration

`consecutive_up_periods`：从最近一期向前，严格高于前一期的连续期数。

示例：连续 4 周 FPD7 环比上涨 → `segment_health = deteriorating`（当 ≥ 4）。

---

## 6. Segment Health Classification

优先级（先匹配先返回）：

| 条件 | segment_health |
|------|----------------|
| volatility_level = high 且 regime_shift_detected | unstable |
| consecutive_up_periods ≥ 4 | deteriorating |
| stability_score ≥ 0.7 且 volatility = low 且无 regime shift 且连续上涨 < 2 且趋势非 upward | healthy |
| volatility_level = medium | watchlist |
| volatility = high 或 stability < 0.4 | unstable |
| 趋势 upward 且连续上涨 ≥ 2 | deteriorating |
| 其余 | watchlist |

`trend_direction`：对索引最小二乘斜率，阈值同 trend_engine。

---

## 7. Findings Schema

`SegmentStabilityFinding`（extends `BaseFinding`）：

| 字段 | 说明 |
|------|------|
| dimension_name | channel / score_band / product / region / user_segment |
| dimension_value | segment 取值 |
| stability_score | 0~1 |
| volatility_score | CV |
| volatility_level | low / medium / high |
| trend_direction | upward / downward / stable |
| consecutive_up_periods | 连续上涨期数 |
| regime_shift_detected | bool |
| segment_health | healthy / watchlist / deteriorating / unstable |
| current_metric_value | 最近一期值 |
| baseline_metric_value | 历史窗口均值 |
| summary | 中文确定性摘要 |

`SegmentStabilityResult`：`top_unstable_segments` 按不稳定程度排序（health 优先、stability 升序）。

---

## 8. 调用示例

```python
from tools.db.contribution.session import get_session
from skill_runtime.segment_stability import SegmentStabilitySkill

with get_session() as session:
    result = SegmentStabilitySkill(session).run(
        metric_name="fpd7",
        dimension_name="channel",
        window_days=60,
        top_n=10,
    )
    for f in result.top_unstable_segments:
        print(f.dimension_value, f.stability_score, f.segment_health)
```

示例输出字段：

```json
{
  "dimension_value": "partner_X",
  "stability_score": 0.28,
  "volatility_level": "high",
  "regime_shift_detected": true,
  "segment_health": "unstable"
}
```

---

## 9. Future Extensions

- 接入 investigation workflow（在 dimension_contribution 之后）
- 与 contribution top contributors 交叉过滤（只分析高贡献 segment）
- 按 metric_profile 配置 CV / regime 阈值
- 日粒度稳定性（当前默认周聚合）
