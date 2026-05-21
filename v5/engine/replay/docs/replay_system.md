# Investigation Replay System

Deterministic replay layer for post-hoc investigation explainability.

## Capabilities

- Historical investigation timeline replay
- Historical findings replay (cumulative at each step)
- Workflow execution replay (skill start/complete/skip)
- Report generation replay

## Core types

- `ReplayTimelineEvent` — ordered playback unit with `event_kind`, `category`, `skill_name`, `payload`
- `InvestigationReplay` — full session with `events[]` sorted by `sequence_index` and `timestamp`

## Builder

`ReplayBuilder.build_from_payload(report_json)` reads persisted `InvestigationResult` and emits:

1. `workflow_started`
2. Skill events from `timeline` (or synthesized from `executed_skills`)
3. `finding_discovered` per skill output
4. `workflow_completed`
5. `report_generated`

## API

`GET /api/investigations/{id}/replay`

## Frontend

`/replay/[id]` — playback controls (play / pause / step forward / backward) and panels for timeline, findings evolution, workflow, and report.
