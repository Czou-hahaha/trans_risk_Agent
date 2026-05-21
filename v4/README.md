# AI Risk Investigation Workspace — V4

**独立可运行目录**：从 V3 拆出跑通「全流程调查」所需代码，V4 编排与 Workspace 更新**仅维护在本文件夹**。

## 与 V3 的关系

| 项目 | 说明 |
|------|------|
| `v3/` | 历史开发目录，可与 V4 并行存在 |
| `v4/` | **推荐运行入口** — 含完整 engine + backend + frontend |

## 架构

```text
v4/
├── .env.example              # 环境变量模板（复制为 .env）
├── MANIFEST.md               # 全流程文件清单
├── docker-compose.yml
├── scripts/start-all.sh      # 一键启动
├── engine/                   # 确定性 skills + V4 workflow + report
├── backend/                  # FastAPI 持久化 + /api/investigation/*
├── frontend/                 # Investigation Workspace UI
└── docs/
    └── investigation_workflow.md
```

## 全流程（确定性编排）

```text
metric_monitor
  → trend_analysis
  → dimension_contribution
  → segment_stability
  → strategy_impact
  → finding_summary
  → report_builder
```

入口：

```python
from workflow.investigation_workflow import InvestigationWorkflow

result = InvestigationWorkflow.run(
    metric_name="fpd7",
    analysis_date="2026-05-20",
)
```

CLI：

```bash
cd v4
source .venv/bin/activate
python engine/scripts/run_investigation.py --metric fpd7 --analysis-date 2026-05-20
```

## 快速开始

### 1. 环境

```bash
cd v4
cp .env.example .env
# 编辑 .env：数据库 URL、DEEPSEEK_API_KEY（finding_summary 可选）
```

Python 3.11+，Postgres `:5433`（或 `docker compose up -d`）。

### 2. 依赖与数据

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r engine/requirements.txt -r backend/requirements.txt

# 从项目根目录 pkl 灌库（路径见 seed 脚本说明）
python engine/tools/seed/seed_from_pkl.py
```

### 3. 一键启动

```bash
./scripts/start-all.sh
```

- 前端：http://localhost:8000  
- API：http://localhost:8001  
- Workspace：http://localhost:8000/investigation  

### 4. API

| 方法 | 路径 |
|------|------|
| POST | `/api/investigation/run` |
| GET | `/api/investigation/{id}` |
| GET | `/api/investigation/{id}/report` |
| POST | `/api/investigations`（兼容） |

## 测试

```bash
cd engine
python -m pytest tests/test_investigation_workflow.py tests/test_workflow.py -v -k "not integration"
```

## 文档

- [investigation_workflow.md](docs/investigation_workflow.md) — 路由、Context、Timeline、Report
- [engine/docs/investigation_workflow.md](engine/docs/investigation_workflow.md) — 与上一致（engine 内副本）
