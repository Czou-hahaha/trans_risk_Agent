# V2 — AI 风控调查控制台（Investigation Console）

**本分支 [`V2-version`](https://github.com/Czou-hahaha/trans_risk_Agent/tree/V2-version)** 的代码目录。

## 做什么？

在 **V1 调查引擎** 之上，提供可给业务/面试官演示的 **全栈产品**：

- 输入调查目标（自然语言 goal）→ 自动解析指标 → 跑三阶段 workflow
- **实时 Timeline** 展示 monitor / contribution / summary 进度
- **Dashboard** 汇总 KPI、最新调查、风险告警
- **报告页** 查看结论并导出 Markdown
- 全过程写入 PostgreSQL，可回溯

**V2 不改业务算法**，只增加：API、持久化、前端。

## 相对 V1 的新增能力

| 能力 | 实现位置 |
|------|----------|
| 调查 CRUD + 状态机 | `backend/app/services/investigation_service.py` |
| REST API | `backend/app/api/investigations.py`、`reports.py` |
| 持久化表 | `investigations`、`investigation_steps`、`investigation_reports` |
| Web UI | `frontend/app/dashboard`、`investigation/*`、`reports/*` |
| 一键启动 | `scripts/start-all.sh` |

完整对比表见 [`docs/V1_V2_COMPARISON.md`](../docs/V1_V2_COMPARISON.md)。

## 架构

```text
v2/
├── engine/                 # = V1 的 workflow + skill_runtime + tools（可独立跑）
├── backend/                # FastAPI，调用 engine.workflow.runner
├── frontend/               # Next.js 14 + Tailwind
├── docker-compose.yml      # PostgreSQL（metric + investigation 库）
└── scripts/start-all.sh
```

```text
用户 → Next.js → FastAPI → InvestigationWorkflowRunner → PostgreSQL
                              ↓
                    investigation_steps（每阶段快照）
                              ↓
                    investigation_reports（最终报告）
```

## 快速开始

### 一键启动（推荐）

```bash
cd v2
cp .env.example .env   # 或从 v1 复制，含 DeepSeek、DB URL
./scripts/start-all.sh
```

- 前端：**http://localhost:8000**
- API：**http://localhost:8001**

### 分步启动

见下方「数据库 / Seed / 前后端」——与历史 README 相同。

#### 数据库

```bash
# 若报错 database "risk_investigation" does not exist：
PGPASSWORD=risk psql -h localhost -p 5433 -U risk -d postgres -c 'CREATE DATABASE risk_investigation;'
# 或：docker compose up -d
```

#### Seed + 依赖（Python 3.10+）

```bash
python3.10 -m venv .venv && source .venv/bin/activate
pip install -r engine/requirements.txt -r backend/requirements.txt
python engine/tools/seed/seed_from_pkl.py
```

#### 后端 / 前端

```bash
cd backend && uvicorn app.main:app --reload --port 8001
cd frontend && npm install && npm run dev
```

## 页面一览

| 路径 | 功能 |
|------|------|
| `/dashboard` | KPI、最新调查、风险告警 |
| `/investigation/new` | 输入 goal，发起调查 |
| `/investigation/[id]` | Timeline + 分步详情（轮询） |
| `/reports/[id]` | 报告 + Export Markdown |

## API 一览

- `GET /api/investigations/dashboard`
- `GET /api/investigations`
- `POST /api/investigations`
- `GET /api/investigations/{id}`
- `GET /api/reports/{id}`

## 刻意不包含（面试说明边界）

- 多 Agent 协作、LangGraph、RAG、长期 memory
- 自主 task planning —— 阶段顺序与 V1 相同，**固定三步**

## 与 V1 分支

- 业务逻辑源码：`v2/engine/`（与 `v1/` 同构）
- 算法/规范阅读：也可对照 [`V1-version` 分支](https://github.com/Czou-hahaha/trans_risk_Agent/tree/V1-version) 的 `v1/skills/`
