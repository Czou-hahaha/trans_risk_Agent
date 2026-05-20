# AGENTS.md — AI 风控分析 Agent (v1)

本项目**只**围绕 4 个核心 skill + workflow 搭建。

## 四个核心 Skill（唯一规范来源）

`v1/skills/` 根目录下 4 个文件：

1. `skills/overseas_cashloan_kpi_definitions.md` — KPI 口径
2. `skills/metric_monitor_skill.md` — 监控与调查门控
3. `skills/dimension_contribution_skill.md` — 维度归因
4. `skills/finding_summary_skill.md` — 调查结论（可 LLM）

## Workflow 执行顺序

```text
overseas_cashloan_kpi_definitions → metric_monitor → dimension_contribution → finding_summary
```

```bash
cd v1 && python scripts/run_investigation.py
```

## 代码布局（跑通用）

| 层 | 路径 |
|----|------|
| Skill 规范（文档） | `skills/*.md`（仅上述 4 个） |
| Skill 实现 | `skill_runtime/` |
| 编排 | `workflow/`（说明见 `workflow/README.md`） |
| 模型 | `models/` |
| 数据/引擎 | `tools/` |
| 配置 | `config/`、`.env` |
| LLM | `services/llm.py`、`prompts/` |

不要维护 `agent_skills/`、`*_monitor/skills/` 等历史兼容目录。
