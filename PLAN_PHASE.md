# PLAN_PHASE.md — 13-phase build

Ordered build for Project 1. `CLAUDE.md` wins if a phase disagrees with it. Do not start the next phase until the current phase’s exit criteria pass. After `make demo` exists, every later phase keeps that checkpoint working.

Status values: `not started`, `in progress`, `implemented`, `validated locally`. “Validated locally” means the phase’s tests passed on this machine. It does not mean deployed.

| Phase | Name | Status |
|---|---|---|
| 1 | Runtime skeleton | not started |
| 2 | Persistence and demo data | not started |
| 3 | Identity and request guards | not started |
| 4 | Support API | not started |
| 5 | Knowledge pipeline | not started |
| 6 | Tools and policy | not started |
| 7 | Rules and guardrails | not started |
| 8 | Specialist agents | not started |
| 9 | Workflow graph and trace | not started |
| 10 | Approval and escalation | not started |
| 11 | Memory | not started |
| 12 | Agent console | not started |
| 13 | Evaluation and delivery | not started |

Course documents 00–17 are not in this repo. This plan is the §19 phase plan derived from `CLAUDE.md`. Stage 17 is optional and is not an exit criterion.

---

### Phase 1 — Runtime skeleton

**Goal.** A process that boots offline, logs JSON with `request_id`, and answers health probes.

**Requirements.** F14 (settings hook), N3.

**Files.** `backend/app/main.py`, `backend/app/core/` (`config`, `logging`, `database` stubs), `backend/app/middleware/`, `.env.example`, `pyproject.toml`, `Makefile`, `tests/conftest.py`, `tests/api/test_health.py`.

**Tests.** `/health` and `/health/live` respond without I/O. Every response carries `X-Request-ID`. Settings read `DEMO_MODE` and `LLM_PROVIDER` from the environment. The test harness sets the offline env vars before importing the app.

**Demo checkpoint.** `make backend` serves `/health/live`. `make demo` is not available yet.

**Exit.** Health tests pass offline. `.env.example` lists every variable in `CLAUDE.md` §10.1 with placeholders only.

---

### Phase 2 — Persistence and demo data

**Goal.** One portable data model and a demo database that loads when empty.

**Requirements.** Data model in `CLAUDE.md` §6. Supports F1 and F4.

**Files.** `backend/app/models/entities.py`, `backend/app/repositories/`, `database/schema.sql`, `database/rls_policies.sql`, `database/seed.sql`, `database/migrations/`, `sample_data/*.json`, `sample_data/knowledge_base/*.md`, seed bootstrap in the lifespan.

**Tests.** Startup on an empty SQLite file with `DEMO_MODE=true` loads 13 tickets and 8 customers. Models and `schema.sql` agree on tables and column types. A second startup does not duplicate rows.

**Demo checkpoint.** `make seed` loads sample data. Ticket `CD-1002` and customer records are readable from the database.

**Exit.** `database/schema.sql` is the authority for table count. The §20 table-count question is closed in `MEMORY.md`.

---

### Phase 3 — Identity and request guards

**Goal.** JWT auth, role checks, rate limiting, and audit, in the documented middleware order.

**Requirements.** N1, N2, N6. Viewer prohibition in §18.1.

**Files.** `backend/app/core/security.py`, auth router, rate-limit and audit middleware, demo token issuer.

**Tests.** Missing and bad tokens are rejected. `vic.viewer` receives 403 on a mutating route. An agent token is accepted. A non-GET request writes `audit_logs`. The limiter uses fakeredis.

**Demo checkpoint.** Demo login issues an 8-hour token for the three demo users.

**Exit.** Middleware order is CORS → RequestId → RateLimit → Audit. No service-role secret is returned to the client.

---

### Phase 4 — Support API

**Goal.** Agents can create and read the records the workflow will consume.

**Requirements.** F1, F4 (read side), contract rule in §12.

**Files.** `backend/app/api/` ticket and customer routers, `backend/app/schemas/`, `backend/app/services/`, `docs/API_CONTRACT.md`, `tests/api/` ticket tests.

**Tests.** `POST /api/v1/tickets` accepts email, chat, web, and API channels. List, get, and 404 behave as the contract says. Customer, subscription, workspace, and previous tickets load for a known demo customer. Duplicate run-while-waiting is specified now and enforced in Phase 10.

**Demo checkpoint.** `make seed` then an API call creates a ticket and fetches `CD-1001` through `CD-1013`.

**Exit.** Contract, schemas, and the future `frontend/lib/types.ts` shapes are written together for every route added here.

---

### Phase 5 — Knowledge pipeline

**Goal.** Fifteen articles are chunked, indexed, and retrievable offline.

**Requirements.** F5, F6 (retrieval half).

**Files.** `rag/chunking.py`, `rag/vector_store.py`, `rag/retriever.py`, `rag/ingest.py`, `make ingest`, knowledge search and admin reindex routes.

**Tests.** `tests/rag/` covers ingest count, the expected article for the key queries, `hybrid` / `semantic` / `keyword`, cache, RRF, rerank, and filters. Chunks are heading-split, then 900/150, and prefixed with `"{title} - {heading}"`. Reindex is admin-only and recreates the collection.

**Demo checkpoint.** `make ingest` reports the article and chunk counts. A query for the MFA recovery article returns `CD-1012`’s expected article in the top 3.

**Exit.** Retrieval hit-rate@3 is measured, even if the full eval suite waits for Phase 13. Customer-facing policy claims have an article to cite.

---

### Phase 6 — Tools and policy

**Goal.** Every side effect the agents can take is a registered tool with an explicit approval bit.

**Requirements.** F9 (policy half).

**Files.** `backend/app/tools/` (`policy.py`, registry, tool functions), `integrations/protocols.py`, `integrations/mock/services.py`, `integrations/factory.py`.

**Tests.** `tests/unit/` tool policy: reads need no approval; `update_ticket` needs none; `reset_demo_setting` and `create_refund_request` need approval; unknown tools need approval; a tool exception returns `ToolResult(ok=False)`; timeout uses `TOOL_TIMEOUT_SECONDS`.

**Demo checkpoint.** A direct registry call to `create_refund_request` without `approved=True` does not write a refund.

**Exit.** The same execute path is the one Phase 10 will call after a human approval. No tool bypasses the registry.

---

### Phase 7 — Rules and guardrails

**Goal.** Policy and safety are deterministic before any specialist calls a model.

**Requirements.** F3 (rules), F10 (rule table), N4, N5, N7 (scrub function).

**Files.** `agents/rules.py`, `agents/prompts.py` (`SECURITY_PREAMBLE`, `wrap_untrusted`), `backend/app/core/` guardrails (`scan_for_injection`, `validate_customer_output`, `scrub`).

**Tests.** Category and severity rules. Severity never lowers a model score. Escalation rules match dispute, deletion, security, data loss, legal, and enterprise outage, each with a named team. `CD-1013` is flagged and wrapped as data. Output validation rejects internal URLs, secrets, and another customer’s data, and that failure is defined as risk `high`. `scrub` removes card numbers, API keys, and passwords.

**Demo checkpoint.** A unit run of the escalation rules on `CD-1005`, `CD-1006`, `CD-1009`, and `CD-1011` returns escalation required without a model call.

**Exit.** Grey-area model judgement is the only path left for Phase 8. Policy cases already have a decision.

---

### Phase 8 — Specialist agents

**Goal.** Six specialists each return their Pydantic model through `call_structured`, using the fake provider.

**Requirements.** F2, F3, F4, F5, F6, F7, F8, F14.

**Files.** `agents/specialists/`, `agents/prompts.py`, `backend/app/schemas/workflow.py`, `backend/app/core/llm.py` fake provider, `tests/agents/`, `datasets/eval_cases.json` (initial cases).

**Tests.** One test per specialist: classification plus one-line summary, severity with reason, customer context with no model call, evidence plus similar cases, diagnosis with numbered steps, resolution plan whose actions come from `plan_actions` and whose reply is grounded and validated. Fake provider cost is `0.0`.

**Demo checkpoint.** Each specialist can be invoked on `CD-1002` and `CD-1010` offline. `CD-1010` remains low severity.

**Exit.** No specialist writes SQL. No specialist calls a tool except through `ToolRegistry`. Eval cases use a valid `expected_category`.

---

### Phase 9 — Workflow graph and trace

**Goal.** One graph runs a low-risk ticket to the end, persists state after every node, and records inspectable events.

**Requirements.** F11 (summary node), F13, graph shape in §7.3.

**Files.** `agents/state.py`, `agents/graph.py`, `agents/checkpointer.py`, `agents/nodes/`, workflow service (`create_run`, `start_workflow`), `GET /tickets/{id}/workflow`, `GET /tickets/{id}/events`.

**Tests.** `tests/workflow/` graph shape, routing, and risk levels. A low-risk ticket completes `execute_resolution` → `ticket_summary` → `memory_update` → END. Events include node start/complete, tool, and llm records with duration. Reducers append `errors` and `completed_nodes`. Checkpointer uses `:memory:` under pytest.

**Demo checkpoint.** `POST /tickets/{id}/run` on a low-risk ticket returns 202, and polling `/workflow` reaches the end.

**Exit.** Telemetry failures do not fail the run. Raw prompts are not present in `workflow_events`.

---

### Phase 10 — Approval and escalation

**Goal.** Money and account changes pause for a human. Policy cases escalate by rule.

**Requirements.** F9, F10, N4 on the live path. 409 behaviour in §10.

**Files.** `human_approval` node, `approval_service.decide`, approval routes, `EscalationAgent`, `execute_resolution`, ticket status transitions.

**Tests.** `CD-1002` pauses with `waiting_on_approval` and an `approval_requests` row; approve resumes and runs the refund tool once; reject routes to escalation. A second run during the pause returns 409. Resume of a run that is not paused returns 409. `CD-1005`, `CD-1006`, `CD-1009`, and `CD-1011` escalate without an approval wait. `CD-1013` does not take an export action. Risk is `high` for approval-required plans, policy escalation, critical severity, injection, and failed output validation.

**Demo checkpoint.** `make demo` pauses on `CD-1002`. `make demo TICKET=CD-1005` escalates.

**Exit.** Code before `interrupt()` is idempotent. The approved path and the automatic path share `ToolRegistry.execute`. A viewer token receives 403 on run, approve, and reject.

---

### Phase 11 — Memory

**Goal.** Every completed run recalls prior notes and writes scrubbed, de-duplicated memory.

**Requirements.** F4 (notes), F11 (write), N7.

**Files.** `memory/short_term.py`, `memory/long_term.py`, `memory/memory_service.py`, `customer_context` recall, `memory_update` node.

**Tests.** Recall returns at most 10 notes. A completed run writes a past issue, the first three troubleshooting steps, and a resolution note. Exact duplicates are skipped. Card numbers, API keys, passwords, and raw ticket bodies are absent from `customer_memory`. Retrieval cache keys match `rag:{mode}:{category}:{top_k}:{query}` and expire in 300 seconds. Short-term TTL is 24 hours. Tests use fakeredis.

**Demo checkpoint.** Running `CD-1002` through approval twice does not duplicate the resolution note.

**Exit.** Memory facades are the only writers of `customer_memory`. Notes never include another customer’s data.

---

### Phase 12 — Agent console

**Goal.** One ticket screen covers F12, and the rest of the console is role-aware.

**Requirements.** F12. UI rules in §11.

**Files.** `frontend/app/` pages listed in §11, `frontend/components/`, `frontend/lib/api.ts`, `frontend/lib/types.ts`, `frontend/lib/hooks.ts`, `frontend/__tests__/`.

**Pages.** `/login`, `/dashboard`, `/tickets`, `/tickets/[id]`, `/customers`, `/customers/[id]`, `/knowledge`, `/escalations`, `/agents`, `/audit`, `/settings`, `/api/health`. Navigation is declared once.

**Tests.** StatusPill, EmptyState, WorkflowSteps step derivation, API helper 401 redirect to `/login?reason=expired`, and the network-error retry. Viewer action controls render disabled. Approve and Reject render only when `approval_status` is `pending`.

**Demo checkpoint.** Browser pass, with the backend running: log in as the agent, open `CD-1002`, run the workflow, watch the twelve steps poll, approve, and send the reply. Repeat as the viewer and confirm the actions stay disabled. Check the ticket list and the customer page still show the same ticket state.

**Exit.** The frontend image’s `NEXT_PUBLIC_*` values are treated as build-time. The service-role key is absent from the frontend. No UI-library dependency and no gradients; the hand-written kit in `components/ui/` is the only chrome.

---

### Phase 13 — Evaluation and delivery

**Goal.** The offline quality bar fails the build when missed, and the delivery files exist without claiming a real deployment.

**Requirements.** F2, F5, F8, F10 thresholds; F14; N8. Honest status in §15.1.

**Files.** `tests/evaluation/`, `datasets/eval_cases.json`, `tests/deployment/`, `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`, `deployment/{aws,azure,gcp}`, `deployment/kubernetes`, `deployment/scripts/`, `.github/workflows/` (`test.yml`, `security.yml`, `docker-build.yml`, `terraform-validate.yml`, `_deploy.yml`).

**Tests.** Eval metrics meet the thresholds in `PLAN.md`. Deployment tests check compose services, non-root Dockerfiles, `HEALTHCHECK`, `.env.example` coverage, and that no `.env` is committed. `docker compose config -q` passes. `make terraform-validate` passes locally. `BASE_URL=http://localhost:8000 make smoke` passes against the local stack.

**Demo checkpoint.** `make test`, then `make demo` for `CD-1002` and `make demo TICKET=CD-1005`.

**Exit.** Core Project 1 is complete only when phases 1–13 are validated locally. `MEMORY.md` may say implemented and validated locally. It still says no cloud credentials, nothing applied, and workflows not executed on GitHub, until those things are true. Stage 17 is not required and is not started by this phase.

---

## Traceability check before calling the project done

| ID | Phase that proves it |
|---|---|
| F1 | 4 |
| F2 | 8, 13 |
| F3 | 7, 8 |
| F4 | 4, 8, 11 |
| F5 | 5, 8, 13 |
| F6 | 5, 8 |
| F7 | 8 |
| F8 | 8, 13 |
| F9 | 6, 10 |
| F10 | 7, 10, 13 |
| F11 | 9, 11 |
| F12 | 12 |
| F13 | 9 |
| F14 | 1, 13 |
| N1 | 3 |
| N2 | 3 |
| N3 | 1 |
| N4 | 7, 10 |
| N5 | 7 |
| N6 | 3 |
| N7 | 7, 11 |
| N8 | 13 |
