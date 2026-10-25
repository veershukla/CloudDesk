# MEMORY.md — CloudDesk Project 1

Durable facts for this repository. `CLAUDE.md` wins if this file drifts. Update this file when a decision, demo fact, or delivery status changes. Do not store secrets, customer payloads, or raw ticket bodies here.

## Product

- Fictional SaaS: **CloudDesk** (team collaboration, cloud file storage, billing, workspaces, API access).
- Users of this product are **support agents**. Customers do not use the console in v1.
- Pipeline for every ticket: Understand → Classify → Investigate → Retrieve → Troubleshoot → Decide → Resolve → Act → Escalate → Remember.
- v1 integrations are mocks. The product does not send real email and does not issue real refunds.
- v1 is English-only and has no customer-facing chat widget.
- Business metrics are tracked, never hard-coded: percent of tickets resolved without a human edit, median time to first response, escalation precision, refund approvals per week. Refunds are never zero-touch.

## Locked decisions

- Three tiers: Next.js 15 on `:3000`, FastAPI on `:8000`, then PostgreSQL/SQLite, Redis/fakeredis, Qdrant/in-memory, and `get_llm`.
- The workflow is a LangGraph graph in `agents/graph.py` with six specialists.
- Demo runtime is offline: `LLM_PROVIDER=fake`, `VECTOR_STORE=memory`, `USE_FAKE_REDIS=true`, SQLite, `InMemorySaver` when `CHECKPOINT_DB_PATH=:memory:`.
- SQLAlchemy models stay portable: JSON columns, `String(36)` UUIDs, same code on SQLite and Postgres.
- Postgres DDL in `database/schema.sql` is the cloud schema. SQLite tables are created at startup.
- The backend uses the service-role key on the server. The browser receives only the anon key.
- JWT is HS256. Demo tokens expire in 8 hours.
- Background workflows run in-process for v1.
- Image tags equal the git SHA once delivery exists. Nothing has been built or tagged yet.
- Stage 17 (Agentic DevOps) is optional and depends on stages 13–16. It is outside core Project 1 completion.

## Roles

Enforced by `require_role` in `backend/app/core/security.py` (`viewer 1 < agent 2 < admin 3`).

| Role | Access |
|---|---|
| `viewer` | Read tickets, customers, knowledge, and audit |
| `agent` | Viewer access, plus run workflows, reply, approve/reject, and escalate |
| `admin` | Agent access, plus reindex knowledge and settings |

Demo users: `admin@clouddesk.demo`, `sam.agent@clouddesk.demo`, `vic.viewer@clouddesk.demo`.

## Domain constants

Categories, exactly these ten, defined first in `backend/app/schemas/common.py`:

`login_issue`, `billing`, `api_failure`, `workspace_permissions`, `storage_quota`, `integration`, `feature_request`, `account`, `security`, `other`.

- Statuses: `new`, `in_progress`, `waiting_on_customer`, `waiting_on_approval`, `escalated`, `resolved`, `closed`.
- Severity: `low`, `medium`, `high`, `critical`.
- Channels: `email`, `chat`, `web`, `api`.
- Plans in the demo set: free, pro, business, enterprise. Eight customers. Thirteen tickets.

| Ticket | What it must exercise |
|---|---|
| CD-1001 | Login issue, active incident, enterprise |
| CD-1002 | Billing refund; approval gate on `create_refund_request` |
| CD-1003 | API 429; rate-limit docs |
| CD-1004 | Storage quota and subscription limits |
| CD-1005 | Security; policy escalation |
| CD-1006 | Data loss; policy escalation |
| CD-1007 | Workspace permissions |
| CD-1008 | Integration failure |
| CD-1009 | Account deletion / GDPR; policy escalation |
| CD-1010 | Feature request; low severity by policy |
| CD-1011 | Payment dispute; policy escalation |
| CD-1012 | MFA recovery article |
| CD-1013 | Prompt injection; ticket text stays data |

Policy cases that rules decide, and the model must not override: dispute, deletion, security, data loss, legal, enterprise outage.

## Workflow facts

Graph order:

`understand_ticket` → `classify_severity` → `customer_context` → `knowledge_retrieval` → `troubleshooting` → `resolution_planning` → `risk_check`, then either `escalation`, `human_approval`, or `execute_resolution`, then `ticket_summary` → `memory_update` → END.

- `human_approval` calls `interrupt()`. Resume uses `Command(resume=…)`.
- Rejection of an approval routes to escalation.
- Node ids are the `completed_nodes` values the UI renders.
- `GET /api/v1/agents` is fed by `GRAPH_NODES` / `GRAPH_EDGES`.
- A second run while status is `waiting_on_approval` returns 409. Resuming a run that is not paused returns 409.
- `WorkflowTracer` never raises. Event names: `node_started`, `node_completed`, `tool_called`, `llm_called`, `approval_requested`, `approval_resolved`, `error`, `workflow_completed`.
- Exposed to operators: decisions, tool calls and results, evidence with scores, node timings, token counts, errors.
- Hidden: raw prompts, hidden chain-of-thought, other customers’ data, secrets.

Tools:

| Tool | Writes | Approval |
|---|---|---|
| `get_customer`, `get_subscription`, `get_ticket_history` | no | no |
| `search_docs`, `check_service_status` | no | no |
| `update_ticket` | tickets | no |
| `reset_demo_setting` | workspace admin | yes |
| `create_refund_request` | billing | yes |
| `create_escalation` | escalations | no |

Unknown tools require approval. Timeout is `TOOL_TIMEOUT_SECONDS`.

## RAG and memory facts

- Knowledge source: `sample_data/knowledge_base/*.md` (15 articles) with YAML front-matter `title`, `category`, `tags`, `summary`.
- Chunk on headings, then 900-character windows with 150-character overlap. Prefix each chunk with `"{title} - {heading}"`.
- Retrieval: semantic ∪ BM25 → reciprocal rank fusion (`k=60`) → heuristic rerank → optional LLM rerank → one hit per article.
- Modes: `hybrid` (default), `semantic`, `keyword`.
- Fake embeddings: hashed bag-of-words, 384 dimensions. Changing the embedding model requires admin `POST /knowledge/reindex`, which recreates the collection.
- Evidence fields: `id`, `title`, `source` (`kb://slug#section`), `snippet`, `score`, `url` (`/knowledge/<id>`), `article_id`.
- Customer-facing policy claims cite knowledge articles.
- Short-term memory TTL is 24 hours. Retrieval cache TTL is 300 seconds. Cache key shape: `rag:{mode}:{category}:{top_k}:{query}`.
- Long-term note types: `preference`, `past_issue`, `troubleshooting`, `note`. Recall up to 10 notes. After a run, store the past issue, the first three troubleshooting steps, and a resolution note.
- `SECRET_PATTERNS` covers card numbers, API keys, and passwords.

## Evaluation bar

These fail the build: classification accuracy ≥ 0.80, retrieval hit-rate@3 ≥ 0.75, escalation correctness ≥ 0.90, citation rate ≥ 0.90, grounding rate ≥ 0.90.

Cases live in `datasets/eval_cases.json` and each case needs a valid `expected_category`.

## Environment defaults worth remembering

- `APPROVAL_REQUIRED_FOR_REFUNDS=true`, `MAX_REFUND_WITHOUT_APPROVAL=0`.
- Demo rate limit: `RATE_LIMIT_PER_MINUTE=120`.
- `QDRANT_COLLECTION=clouddesk_knowledge`.
- `get_settings()` is cached. A `.env` change requires a server restart.
- Middleware order, outermost last: CORS → RequestId → RateLimit → Audit.
- Health: `/health`, `/health/live` (no I/O), `/health/ready` (db, redis, vector store, llm).

## Honest status

Update each row in place. Do not mark a row done from intention.

| Surface | State on 2026-10-25 |
|---|---|
| Repository contents | Requirement files are in place (`CLAUDE.md`, `MEMORY.md`, `PLAN.md`, `PLAN_PHASE.md`, `README.md`, `.env.example`, `.cursor/skills/clouddesk-support/SKILL.md` symlinked from `.claude/skills/`, `docs/ARCHITECTURE.md`, `docs/API_CONTRACT.md` draft v0). Application code, tests, and sample data are absent. |
| Implemented | P1-1 settings (`backend/app/core/config.py`) and JSON logging (`backend/app/core/logging.py`), branch `feature/backend-config-logging`, not merged yet. |
| Validated locally | P1-1: `uv run pytest` (23 unit tests) and `uv run ruff check .` pass on 2026-10-25. `make test` and `make demo` do not exist yet. |
| Cloud credentials | None used. |
| Applied to a real account | Nothing. |
| GitHub Actions | Workflow files are not in the repo. None have been executed. |
| Phase plan | Specified in `PLAN_PHASE.md`. All 13 phases are not started. |

## Open questions from `CLAUDE.md` §20

- A Project 1 `README.md` was referenced by the course and was not supplied. Command names in `CLAUDE.md` §14 still need to be checked against it when it appears.
- Course paths `../docs/`, `../deployment-agent/`, and `../shared-infrastructure/` sit outside this repo. They are not copied in yet.
- Table counts disagree across the course notes (16 in the database doc, 15 data tables in the RLS note). `database/schema.sql` becomes the authority once it is written.
- Stage documents 00–17 are not in this repo. `PLAN_PHASE.md` is derived from `CLAUDE.md`, not from those missing files.

## Update protocol

- Record a new locked decision with the date and the requirement id it serves.
- When a phase exits, set its status in `PLAN_PHASE.md` and add one line here under Honest status.
- When a demo ticket’s expected behaviour changes, change the ticket table above and the matching test together.
- Leave secrets, tokens, connection strings, and ticket bodies out of this file.
