# Recurring Pattern Engine — Investigation Intelligence Layer

> **路径**：`v5/engine/intelligence_memory/patterns/`

## 目标

在 **findings persistence** 与 **historical recall** 之上，自动发现跨 investigation 的确定性风险模式，输出 **Historical investigation intelligence**，而非单次调查结果。

**不做**：LLM reasoning、ML、embeddings、vector retrieval、autonomous memory。

## 架构

| 组件 | 职责 |
|------|------|
| `RecurringPatternEngine` | 编排所有 detector，聚合 `DetectedPattern` |
| `PatternRegistry` | 注册支持的 pattern detectors |
| `pattern_detector.py` | 各模式确定性检测逻辑 |
| `schemas/detected_pattern.py` | 对外输出模型 |
| `schemas/pattern_signal.py` | detector 内部证据信号 |

## 支持模式

| `pattern_type` | 说明 | 示例 |
|----------------|------|------|
| `recurring_contributor` | 维度值多次进入 Top-N 贡献者 | partner_X 连续 3 周 Top3 |
| `recurring_segment_instability` | segment 不稳定反复出现 | channel=partner_X 多次 delta_pp 恶化 |
| `strategy_side_effect` | 通过率下滑伴随 FPD 改善 | approval↓ + fpd7↓（改善）反复出现 |
| `approval_risk_shift` | 通过率下滑伴随风险恶化 | approval↓ + fpd7↑ 反复出现 |
| `volume_risk_tradeoff` | 体量损失大于风险改善 | 过紧策略 / over-tightening |

## Confidence Score

确定性公式（非 ML 概率）：

```text
confidence = 0.25 * frequency
           + 0.25 * consistency
           + 0.25 * severity
           + 0.25 * cross_investigation_recurrence
```

各 detector 提供 `severity_cap` 归一化幅度项。

## 使用示例

```python
from intelligence_memory.patterns import RecurringPatternEngine
from intelligence_memory.patterns.pattern_detector import DetectorConfig

engine = RecurringPatternEngine()
patterns = engine.detect_all(
    config=DetectorConfig(window_days=30, min_occurrences=3),
    metric_name="fpd7",
)
summary = engine.summarize_intelligence(patterns)
```

按类型检测：

```python
engine.detect_by_type("volume_risk_tradeoff")
```

## 数据依赖

- `finding_type=dimension_contribution` — contributor 模式
- `finding_type=segment_stability` + `delta_pp` — segment 不稳定
- `finding_type=strategy_impact` — 策略模式；需 `delta_pp`(fpd7)、`approval_delta_pp`、`volume_delta_pct`（`finding_mapper` 持久化）

## 测试

`v5/engine/tests/test_pattern_engine.py` — SQLite 内存库，覆盖五类模式中的核心场景。
