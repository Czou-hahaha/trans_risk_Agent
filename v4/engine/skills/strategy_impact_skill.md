---
name: strategy_impact
description: |
  确定性策略上线影响分析：before/after 指标对比、风险-业务 tradeoff、有效性分类。
  回答「策略上线后通过率/风险/流量变化多少」「这次策略调整是否值得」。
  非 AB 平台、非 ML 优化、非强化学习、非自主策略引擎。
---

# strategy_impact_skill

**Python 实现**：`skill_runtime/strategy_impact.py`  
**工具层**：`tools/engines/strategy_impact_engine.py` · `tools/repositories/strategy_impact_repository.py`  
**模型**：`models/strategy_impact.py`  
**数据**：`strategy_metrics_daily`（长表：`strategy_name`, `metric_date`, `metric_name`, `metric_value`, `sample_size`）

**Status**：可独立运行；尚未接入 `workflow/runner.py`

---

## 1. Skill Purpose

风控策略运营核心能力，属于 **Risk Strategy Intelligence Layer**。

在 segment / 维度分析之后，回答：

- 某次策略动作（如 `RISK_003`）上线后，**通过率、FPD7、业务量** 各变化多少？
- 每损失 1pp 通过率，换来多少风险下降（**risk reduction efficiency**）？
- 本次收紧是否 **值得**（`highly_effective` / `effective` / `over_tightened` / …）？

```text
（规划）metric_monitor → trend_analysis → dimension_contribution
         → segment_stability → strategy_impact → finding_summary
（当前）StrategyImpactSkill.run(...) 独立调用
```

---

## 2. Before-After Methodology

以 `deployment_date` 为界：

| 窗口 | 区间（默认各 14 天） |
|------|----------------------|
| Before | `[deploy - before_window_days, deploy - 1]` |
| After  | `[deploy, deploy + after_window_days - 1]` |

流程：

```text
strategy_metrics_daily
  → StrategyImpactRepository（仅此处 SQL）
  → StrategyImpactEngine.aggregate_before_after_metrics（按 sample_size 加权）
  → calculate_metric_delta / tradeoff / classify / 中文确定性 summary
  → StrategyImpactFinding
```

禁止：AB 实验框架、因果推断、ML、RL、LangChain Agent、LLM 摘要。

---

## 3. Tradeoff Analysis

| 指标 | 业务含义 | Delta 形式 |
|------|----------|------------|
| `approval_rate` | 通过率 | `delta_pp`（百分点） |
| `fpd7` | 7 日首逾风险 | `delta_pp`（下降为改善） |
| `volume` | 申请/放款量 | `delta_pct`（相对变化 %） |

**Risk reduction efficiency**（核心 tradeoff）：

```text
fpd7_reduction_pp / approval_loss_pp
```

若通过率几乎未降，则回退为 `fpd7_reduction / volume_loss_pct`。

---

## 4. Effectiveness Classification

确定性规则（`StrategyImpactEngine.classify_strategy_effectiveness`）：

| 条件 | classification |
|------|----------------|
| 核心指标波动均低于噪声阈值 | `neutral` |
| 风险未实质改善 | `ineffective` |
| FPD7 显著下降 + 通过率/流量损失很小 | `highly_effective` |
| 风险下降 + 业务影响可接受 | `effective` |
| 业务损失大 + 风险改善有限 | `over_tightened` |

阈值见 `StrategyImpactEngineConfig`（`tools/engines/strategy_impact_engine.py`）。

---

## 5. Risk Reduction Efficiency

示例：

```text
approval_rate -3.2pp，fpd7 -1.1pp
→ efficiency ≈ 1.1 / 3.2 ≈ 0.34
```

解读：每牺牲约 1pp 通过率，约带来 0.34pp FPD7 下降（越高越划算）。

---

## 6. Findings Schema

`StrategyImpactFinding`（继承 `BaseFinding`）核心字段：

- `strategy_name`, `deployment_date`, `before_window_days`, `after_window_days`
- `approval_rate_before/after`, `approval_delta_pp`
- `fpd7_before/after`, `fpd7_delta_pp`
- `volume_before/after`, `volume_delta_pct`
- `risk_reduction_efficiency`, `strategy_effectiveness`, `summary`

`StrategyImpactResult`：`findings` 列表 + `generated_at`。

---

## 7. Usage

```python
from datetime import date
from skill_runtime.strategy_impact import StrategyImpactSkill
from tools.db.monitor.session import get_session

with get_session() as session:
    result = StrategyImpactSkill(session).run(
        strategy_name="RISK_003",
        deployment_date=date(2026, 5, 10),
        before_window_days=14,
        after_window_days=14,
    )
finding = result.findings[0]
# finding.fpd7_delta_pp, finding.approval_delta_pp, finding.strategy_effectiveness
```

---

## 8. Future Extensions

- 接入 `workflow/runner.py`（在 `segment_stability` 之后、`finding_summary` 之前）
- 按 `channel` 等维度拆分的策略影响（需宽表扩展）
- `rule_hit_rate` / `gmv` 等多指标并行 finding
- 与策略元数据表（owner、hypothesis）关联的复盘看板
