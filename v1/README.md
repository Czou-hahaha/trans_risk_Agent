# AI 风控调查流水线 — V1

围绕 **4 个 skill 文档** + **workflow 代码** 的最小结构。

```text
v1/
├── skills/                 # 4 个 *.md 规范（见 AGENTS.md）
├── skill_runtime/          # metric_monitor · dimension_contribution · finding_summary
├── workflow/               # 流水线编排（见 workflow/README.md）
├── models/                 # Pydantic 数据结构
├── tools/                  # DB、贡献引擎、seed
├── config/                 # 设置
├── services/               # LLM
├── prompts/                # finding_summary 提示词
├── scripts/run_investigation.py
├── tests/
└── docker-compose.yml
```

## 快速开始

```bash
cd v1
pip install -r requirements.txt
docker compose up -d
python tools/seed/seed_from_pkl.py
python scripts/run_investigation.py
```

索引：`AGENTS.md` · `skills/README.md` · `workflow/README.md`
