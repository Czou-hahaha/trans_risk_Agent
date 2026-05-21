# trans_risk_Agent — V4（七阶段调查 + Investigation Workspace）

[![V4 分支](https://img.shields.io/badge/branch-V4--version-green)](https://github.com/Czou-hahaha/trans_risk_Agent/tree/V4-version)

**推荐运行入口（V4 时代）**：完整 engine + backend + frontend，七阶段确定性编排。

## 克隆本版本

```bash
git clone -b V4-version git@github.com:Czou-hahaha/trans_risk_Agent.git
cd trans_risk_Agent/v4
cp .env.example .env
```

## 架构

```text
v4/
├── .env.example
├── MANIFEST.md               # 全流程文件清单
├── docker-compose.yml
├── scripts/start-all.sh
├── engine/                   # skills + workflow + report
├── backend/                  # FastAPI
├── frontend/                 # Investigation Workspace
└── docs/investigation_workflow.md
```

## 全流程（确定性编排）

```text
metric_monitor → trend_analysis → dimension_contribution
  → segment_stability → strategy_impact → finding_summary → report_builder
```

CLI：

```bash
cd v4
source .venv/bin/activate
python engine/scripts/run_investigation.py --metric fpd7 --analysis-date 2026-05-20
```

## 快速开始

```bash
cd v4
cp .env.example .env
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r engine/requirements.txt -r backend/requirements.txt
python engine/tools/seed/seed_from_pkl.py
./scripts/start-all.sh
```

- 前端：http://localhost:8000  
- API：http://localhost:8001  
- Workspace：http://localhost:8000/investigation  

## API

| 方法 | 路径 |
|------|------|
| POST | `/api/investigation/run` |
| GET | `/api/investigation/{id}` |
| GET | `/api/investigation/{id}/report` |

## 测试

```bash
cd v4/engine
python -m pytest tests/test_investigation_workflow.py tests/test_workflow.py -v -k "not integration"
```

## 文档

- [docs/investigation_workflow.md](v4/docs/investigation_workflow.md)
- [v4/README.md](v4/README.md) — 目录内详细说明

## 其他版本

| 分支 | 说明 |
|------|------|
| [V3-version](https://github.com/Czou-hahaha/trans_risk_Agent/tree/V3-version) | V2 + 趋势分析 skill |
| [V5-version](https://github.com/Czou-hahaha/trans_risk_Agent/tree/V5-version) | V4 + Risk Intelligence 持久化 |
