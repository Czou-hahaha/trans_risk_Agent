# trans_risk_Agent — V5（全流程 + Findings 持久化 + 产品前端）

[![V5 分支](https://img.shields.io/badge/branch-V5--version-purple)](https://github.com/Czou-hahaha/trans_risk_Agent/tree/V5-version)

**当前推荐运行入口**：V4 全流程 + **Risk Intelligence Storage Layer**（结构化 findings 写入 Postgres）。

## 克隆本版本

```bash
git clone -b V5-version git@github.com:Czou-hahaha/trans_risk_Agent.git
cd trans_risk_Agent/v5
cp .env.example .env
```

## 架构

```text
v5/
├── .env.example
├── MANIFEST.md
├── docker-compose.yml
├── scripts/start-all.sh
├── engine/
│   ├── intelligence_memory/   # V5 findings 持久化
│   ├── workflow/
│   └── ...
├── backend/
├── frontend/                  # Dashboard / Workspace / Replay / Executive
└── docs/
```

## V5 新增

Workflow 完成后自动持久化 `InvestigationContext.findings`：

- `stored_findings`
- `investigation_snapshots`

详见 `engine/intelligence_memory/docs/findings_persistence.md`。

## 全流程

```text
metric_monitor → trend_analysis → dimension_contribution
  → segment_stability → strategy_impact → finding_summary → report_builder
  → [V5] persist findings
```

## 快速开始

```bash
cd v5
cp .env.example .env
docker compose up -d
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r engine/requirements.txt -r backend/requirements.txt
python engine/tools/seed/seed_from_pkl.py
./scripts/start-all.sh
```

## 测试

```bash
cd v5/engine
python -m pytest tests/test_findings_persistence.py tests/test_investigation_workflow.py -v -k "not integration"
```

前端验收（可选，需 Node + Playwright）：

```bash
cd tests/frontend_acceptance && npm install && npx playwright install chromium
python acceptance_runner.py
```

## 其他版本

| 分支 | 说明 |
|------|------|
| [V4-version](https://github.com/Czou-hahaha/trans_risk_Agent/tree/V4-version) | 七阶段编排（无 intelligence_memory） |
| [V3-version](https://github.com/Czou-hahaha/trans_risk_Agent/tree/V3-version) | 趋势分析 + V2 控制台 |
