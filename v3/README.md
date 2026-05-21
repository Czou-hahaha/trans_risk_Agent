# AI Investigation Console — V3

在 V2 基础上增加 **trend_analysis_skill**（确定性时序风险分析），并保留 V2 可跑通的全流程（monitor → contribution → summary + 前后端）。

## 架构

```text
v3/
├── .env                    # 从 V2 复制（含 DeepSeek、DB URLs）
├── engine/                 # workflow；趋势分析在 tools + skill_runtime（无独立大包）
├── backend/                # FastAPI + PostgreSQL 持久化
├── frontend/               # Next.js 14 + Tailwind + shadcn 风格组件
└── docker-compose.yml      # PostgreSQL（metric / contribution / investigation 库）
```

## 快速开始

### 一键启动（推荐）

```bash
cd v3
./scripts/start-all.sh
```

浏览器打开 **http://localhost:8000**（前端），API 在 **http://localhost:8001**。

### 1. 数据库

本地已有 Postgres `:5433` 时可跳过 Docker。首次需有库：

```bash
# 若报错 database "risk_investigation" does not exist：
PGPASSWORD=risk psql -h localhost -p 5433 -U risk -d postgres -c 'CREATE DATABASE risk_investigation;'
```

或用 Docker：`docker compose up -d`（会自动建库）。

### 2. 安装依赖并 Seed 指标数据

需要 **Python 3.10+**（engine 使用 `float | None` 语法；勿用系统 3.9 建 venv）。

```bash
/Library/Frameworks/Python.framework/Versions/3.10/bin/python3 -m venv .venv
source .venv/bin/activate
pip install -r engine/requirements.txt -r backend/requirements.txt

# 需要项目根目录的 pkl 数据文件
python engine/tools/seed/seed_from_pkl.py
```

### 3. 启动后端

```bash
cd backend
uvicorn app.main:app --reload --port 8001
```

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 http://localhost:8000（前端）；API 后端 http://localhost:8001

## 页面

| 路径 | 功能 |
|------|------|
| `/dashboard` | KPI、最新调查、风险告警、报告 |
| `/investigation/new` | 输入目标，Run Investigation |
| `/investigation/[id]` | 左侧 Timeline + 右侧 Step 详情（polling） |
| `/reports/[id]` | 报告 + Export Markdown |

## API

- `GET /api/investigations/dashboard`
- `GET /api/investigations`
- `POST /api/investigations`
- `GET /api/investigations/{id}`
- `GET /api/reports/{id}`

## 数据库表

- `investigations` — 调查任务与 workflow 状态
- `investigation_steps` — monitor / contribution / summary 各阶段输出
- `investigation_reports` — 最终报告 JSON

## V3 新增：Trend Analysis

独立运行（尚未接入 workflow）：

```bash
cd v3/engine
pytest tests/test_trend_engine.py tests/test_trend_analysis_skill.py -q
```

详见 `engine/skills/trend_analysis_skill.md`。

## V3 不包含（与 V2 相同）

多 Agent、LangGraph、RAG、memory、autonomous planning — 仅 **workflow 可视化 + 持久化**。
