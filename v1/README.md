# V1 — AI 风控调查流水线（Deterministic Workflow）

**本分支 [`V1-version`](https://github.com/Czou-hahaha/trans_risk_Agent/tree/V1-version)** 的代码目录。

## 做什么？

把海外现金贷风控分析师的固定工作流自动化：

1. **读 KPI 口径**（FPD7、通过率等定义在 Skill 文档里）
2. **监控**：对比当前周 vs 上周，按 \|Δ\| 门控决定是否调查
3. **归因**：按渠道/产品等维度算贡献度排序
4. **结论**：生成结构化 `InvestigationConclusion`（末段可接 DeepSeek）

**不是** 聊天机器人，**是** 可复现、可单测的 **pipeline**。

## 三阶段流水线

```text
metric_monitor → dimension_contribution → finding_summary
```

- 门控：`needs_investigation == false` 时直接结束，不跑归因
- 编排：`workflow/runner.py`（无 LangGraph / 无多 Agent）
- 规范来源：`skills/*.md`（4 个文件，见 `AGENTS.md`）

## 目录结构

```text
v1/
├── skills/                 # 业务规范（metric_monitor / contribution / summary / KPI 定义）
├── skill_runtime/          # 三阶段 Python 实现
├── workflow/               # InvestigationWorkflowRunner 编排
├── models/                 # Pydantic：Finding、Conclusion、Result
├── tools/                  # DB、贡献引擎、seed_from_pkl
├── services/llm.py         # 仅 finding_summary 使用
├── scripts/run_investigation.py   # 入口
├── tests/                  # workflow + 维度覆盖
└── docker-compose.yml      # PostgreSQL :5433
```

## 快速开始

```bash
cd v1
cp .env.example .env          # DEEPSEEK_API_KEY、数据库连接
pip install -r requirements.txt
docker compose up -d
python tools/seed/seed_from_pkl.py   # 需准备指标 pkl（见项目说明）
python scripts/run_investigation.py
```

## 关键输出

运行成功后得到 `InvestigationResult`，包含：

- `monitor_finding` — 是否异常、delta_pp、归因意图
- `contributions` — 维度贡献列表（若进入调查）
- `conclusion` — 标题、摘要、建议动作（若进入调查）

## 与 V2 的关系

| V1 提供 | V2 在此基础上增加 |
|---------|-------------------|
| 三阶段引擎与 Skill 规范 | FastAPI 持久化 + Next.js 控制台 |
| CLI 验证 | Dashboard / Timeline / 报告导出 |

详见 [`docs/V1_V2_COMPARISON.md`](../docs/V1_V2_COMPARISON.md) 或 [V2-version 分支](https://github.com/Czou-hahaha/trans_risk_Agent/tree/V2-version)。

## 文档索引

- `AGENTS.md` — 四个 Skill 与代码映射
- `workflow/README.md` — 编排设计与阶段定义
- `skills/README.md` — Skill 列表
