# CloudDesk - Autonomous Customer Support & Resolution Platform

An AI support-resolution console for a fictional SaaS company, **CloudDesk**. A ticket arrives, a
LangGraph workflow of six specialist agents investigates it and proposes a resolution, and a human
support agent approves anything that costs money or touches an account.

```text
Understand → Classify → Investigate → Retrieve → Troubleshoot → Decide → Resolve → Act → Escalate → Remember
```

Stack: Next.js 15 · FastAPI · LangGraph/LangChain · SQLAlchemy 2 (SQLite/Postgres) · Redis · Qdrant.
Runs fully offline in `DEMO_MODE` with no API key.

> **Status:** planning. The spec and plans are written; application code has not been started.
> See [`MEMORY.md`](MEMORY.md) for the honest status and [`PLAN_PHASE.md`](PLAN_PHASE.md) for progress.

## Documents

| File | What it is |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | The spec - single source of truth |
| [`PLAN.md`](PLAN.md) | Requirement catalog (F1–F14, N1–N8) and exit bar |
| [`PLAN_PHASE.md`](PLAN_PHASE.md) | 13-phase build order |
| [`TASKS.md`](TASKS.md) | Sub-task tracker with one feature branch per task |
| [`MEMORY.md`](MEMORY.md) | Locked decisions and honest status |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Component, workflow and infrastructure diagrams |
| [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md) | Every route and type |
| [`.cursor/skills/clouddesk-support/SKILL.md`](.cursor/skills/clouddesk-support/SKILL.md) | Procedure for AI coding agents working in this repo |
| [`Git_GitHub_Workflow_Guide.md`](Git_GitHub_Workflow_Guide.md) | Branching and PR flow |

## Quick start (once Phase 1 lands)

```bash
cp .env.example .env
make setup            # .venv + deps + .env
make seed             # load sample data into DB
make ingest           # chunk + index knowledge base
make backend          # FastAPI on :8000
make test             # offline pytest
make demo             # CD-1002 refund end-to-end (pauses for approval)
cd frontend && npm run dev
```

Demo users: `admin@clouddesk.demo`, `sam.agent@clouddesk.demo`, `vic.viewer@clouddesk.demo`.

The `make` targets do not exist yet; they are defined in `CLAUDE.md` §14.

## Contributing

Branch from `development`, open PRs against `development`; `development` → `testing` → `main`.
Never commit `.env`, `data/`, `*.db`, `terraform.tfvars`, `backend.hcl`, `tfplan` or any real key.
