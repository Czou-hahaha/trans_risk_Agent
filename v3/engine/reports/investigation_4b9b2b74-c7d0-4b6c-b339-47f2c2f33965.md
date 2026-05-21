# Risk Investigation Report — FPD7

**Investigation ID:** `4b9b2b74-c7d0-4b6c-b339-47f2c2f33965`  
**Analysis Date:** 2026-03-07

## Executive Summary
Portfolio FPD7 showed 1.60pp improvement (current 10.11% vs prior 11.71%). The move was primarily driven by order_tag=test (contribution -1.51pp). Recommended focus: 核查order_tag=test的订单来源及近期业务调整，确认是否为主动关停测试渠道或收紧准入规则，并评估对业务量的长期影响。

## Trend Analysis
FPD7 在近期呈现强下降趋势，波动性中，最新滚动均值较基线变动 -2.83pp。

- Direction: downward
- Strength: strong
- Rolling change: -2.83pp
- Consecutive up periods: 0

## Key Contributors
Top 5 contributors ranked by absolute contribution.

- #1 order_tag=test: contribution -1.51pp, delta -4.36pp
- #2 floan_period=8.0: contribution -0.78pp, delta -3.02pp
- #3 order_tag=online: contribution -0.69pp, delta -1.58pp
- #4 risk_level=6.0: contribution -0.65pp, delta -4.37pp
- #5 risk_level=2.0: contribution -0.49pp, delta -3.32pp

## Segment Stability
Segment stability review did not flag material instability.

_No items._

## Strategy Impact
No nearby strategy deployment impact analysis was available.

_No items._

## Risk Recommendations
order_tag=test订单量锐减68%且风险大幅下降，可能源于该标签对应的测试类或特定渠道订单被主动收紧或暂停，导致高风险样本退出；同时floan_period=8.0和risk_level=6.0等高风险段订单量同步减少，暗示风控策略或审批标准在近期有所调整。

- 核查order_tag=test的订单来源及近期业务调整，确认是否为主动关停测试渠道或收紧准入规则，并评估对业务量的长期影响。
- 分析floan_period=8.0（贷款期限8个月）订单量下降原因，判断是否为产品策略调整或客户需求变化，避免误伤优质客户。
- 监控risk_level=6.0和2.0等风险等级订单的后续表现，确认风险改善是否可持续，防止样本偏移导致的虚假改善。