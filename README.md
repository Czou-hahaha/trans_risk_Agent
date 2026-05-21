# trans_risk_Agent — V3（趋势分析 + 全流程控制台）

[![V3 分支](https://img.shields.io/badge/branch-V3--version-blue)](https://github.com/Czou-hahaha/trans_risk_Agent/tree/V3-version)

在 V2 基础上增加 **trend_analysis_skill**（确定性时序风险分析），并保留可跑通的全流程（monitor → contribution → summary + 前后端）。

## 克隆本版本

```bash
git clone -b V3-version git@github.com:Czou-hahaha/trans_risk_Agent.git
cd trans_risk_Agent/v3
cp .env.example .env   # 填入数据库 URL、DEEPSEEK_API_KEY
```

## 架构

```text
v3/
├── .env.example            # 复制为 .env（勿提交密钥）
├── engine/                 # workflow；趋势分析在 tools + skill_runtime
├── backend/                # FastAPI + PostgreSQL 持久化
├── frontend/               # Next.js 14 + Tailwind
├── docker-compose.yml      # PostgreSQL
└── scripts/start-all.sh    # 一键启动
```

## 快速开始

### 一键启动（推荐）

```bash
cd v3
./scripts/start-all.sh
```

- 前端：http://localhost:8000  
- API：http://localhost:8001  

### 手动步骤

**1. 数据库**

本地 Postgres `:5433` 或 `docker compose up -d`。首次建库：

```bash
PGPASSWORD=risk psql -h localhost -p 5433 -U risk -d postgres -c 'CREATE DATABASE risk_investigation;'
```

**2. Python 依赖与 Seed**

需要 **Python 3.10+**：

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r engine/requirements.txt -r backend/requirements.txt

# 将项目根目录的指标 pkl 放在约定路径后执行
python engine/tools/seed/seed_from_pkl.py
```

**3. 分别启动**

```bash
cd backend && uvicorn app.main:app --reload --port 8001
cd frontend && npm install && npm run dev
```

## 页面

| 路径 | 功能 |
|------|------|
| `/dashboard` | KPI、最新调查、风险告警 |
| `/investigation/new` | 发起调查 |
| `/investigation/[id]` | Timeline + Step 详情 |
| `/reports/[id]` | 报告 + Export Markdown |

## V3 新增：Trend Analysis

```bash
cd v3/engine
pytest tests/test_trend_engine.py tests/test_trend_analysis_skill.py -q
```

详见 `engine/skills/trend_analysis_skill.md`。

## 其他版本

| 分支 | 说明 |
|------|------|
| [V1-version](https://github.com/Czou-hahaha/trans_risk_Agent/tree/V1-version) | CLI 流水线 MVP |
| [V2-version](https://github.com/Czou-hahaha/trans_risk_Agent/tree/V2-version) | 调查控制台 |
| [V4-version](https://github.com/Czou-hahaha/trans_risk_Agent/tree/V4-version) | 七阶段确定性编排 + Workspace |
| [V5-version](https://github.com/Czou-hahaha/trans_risk_Agent/tree/V5-version) | V4 + Findings 持久化层 |
