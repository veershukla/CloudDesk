# PLAN.md — CloudDesk Project 1

Build plan for the autonomous support-resolution platform. `CLAUDE.md` is the spec. `PLAN_PHASE.md` is the order of work. This file is the requirement catalog and the exit bar for the whole project.

## Goal

Ship an agent console where a support agent opens a CloudDesk ticket, runs one workflow, inspects every step, and approves anything that spends money or changes an account. The same codebase runs offline with no API key.

## Users

| Actor | Outcome |
|---|---|
| Viewer | Can read tickets, customers, knowledge, and audit, and cannot run, reply, or approve |
| Agent | Can run the workflow, reply, request information, approve or reject, and escalate from one ticket screen |
| Admin | Can reindex knowledge and change settings |
| Platform | Records an audit row for every state-changing request and an event for every node, tool call, and model call |

## Non-goals for v1

- Real email delivery and real refunds.
- Languages other than English.
- A customer-facing chat widget.
- A separate worker process for workflows.
- Applying Terraform to a live cloud account.
- The Stage 17 deployment agent (`../deployment-agent/`).

## System requirements

### Functional

| ID | The system shall | Proven by | Phase |
|---|---|---|---|
| F1 | Create a ticket from email, chat, web, or API via `POST /api/v1/tickets` | API ticket-create test | 4 |
| F2 | Classify the ticket into one of the ten categories and write a one-line summary | Supervisor agent test; classification accuracy ≥ 0.80 | 8, 13 |
| F3 | Assign severity `low`/`medium`/`high`/`critical` with a reason; rules may only raise it | Rules test; `CD-1010` stays low | 7, 8 |
| F4 | Load customer, subscription, workspace, previous tickets, and up to 10 memory notes | Customer agent test | 4, 8, 11 |
| F5 | Attach cited evidence from hybrid retrieval, reranked, one hit per article | RAG tests; hit-rate@3 ≥ 0.75 | 5, 8, 13 |
| F6 | Attach similar previously resolved cases | `KnowledgeAgent.similar_cases` test | 5, 8 |
| F7 | Produce probable causes and numbered troubleshooting steps | Troubleshooting agent test | 8 |
| F8 | Produce a resolution plan: summary, customer reply, internal notes, and actions | Resolution agent test; grounding rate ≥ 0.90 | 8, 13 |
| F9 | Hold consequential actions for a recorded human approval | Policy unit test; `CD-1002` pause and resume | 6, 10 |
| F10 | Escalate policy cases to a named team; rules override the model | Escalation correctness ≥ 0.90; `CD-1005`, `CD-1006`, `CD-1009`, `CD-1011` | 7, 10, 13 |
| F11 | Write a ticket summary and update customer memory after every completed run | Workflow end-state test; memory scrub test | 9, 11 |
| F12 | Let an agent approve, reject, escalate, reply, and request information from one screen | Frontend tests plus a browser pass of `/tickets/[id]` | 12 |
| F13 | Record every node, tool call, and model call with timing, tokens, and cost | `GET /tickets/{id}/events` test | 9 |
| F14 | Complete a run in `DEMO_MODE` with the fake provider and no API key | Offline pytest and `make demo` | 1, 13 |

### Non-functional

| ID | The system shall | Proven by | Phase |
|---|---|---|---|
| N1 | Authenticate with Supabase-compatible JWT (HS256) | Auth API tests | 3 |
| N2 | Rate-limit clients with a fixed window in Redis | Rate-limit test; demo ceiling 120/min | 3 |
| N3 | Send `X-Request-ID` on every response | Request-id test | 1 |
| N4 | Treat ticket text as data and contain prompt injection | `CD-1013` test | 7, 10 |
| N5 | Validate customer-facing output before a reply is shown | Guardrail unit test; failed validation raises risk to `high` | 7 |
| N6 | Audit every non-GET request | Audit middleware test | 3 |
| N7 | Keep secrets out of memory notes | Scrub test with card, key, and password fixtures | 11 |
| N8 | Build as containers that can be deployed to AWS, Azure, and GCP | Dockerfile and compose tests; Terraform validate | 13 |

### Quality bar

| Metric | Threshold |
|---|---|
| Classification accuracy | ≥ 0.80 |
| Retrieval hit-rate@3 | ≥ 0.75 |
| Escalation correctness | ≥ 0.90 |
| Citation rate | ≥ 0.90 |
| Grounding rate (steps present in the reply) | ≥ 0.90 |

Pytest uses `asyncio_mode = "auto"` and `loop_scope = "session"`. Do not add `@pytest.mark.asyncio` with a different scope.

## Workstreams

Work proceeds in `PLAN_PHASE.md`. The dependency order is:

1. Runtime, so later code has settings, logs, health, and an offline test harness.
2. Data, so APIs and agents share one model.
3. Auth and audit, so every later route is protected.
4. Ticket and customer APIs, so there is something to run.
5. RAG, so evidence exists before agents cite it.
6. Tools and policy, so agents cannot invent side effects.
7. Rules and guardrails, so policy exists before any model call.
8. Specialists, one Pydantic result each.
9. The graph, checkpointer, and event trace.
10. Approval interrupt and policy escalation.
11. Memory read and write.
12. The agent console.
13. Evaluation thresholds, containers, and delivery scaffolding.

Stages 13–16 of the course (containers, observability, CI, multi-cloud) are represented inside Phase 13 as files and local validation. Stage 17 stays optional and unbuilt.

## Request path the plan must preserve

1. `POST /api/v1/tickets/{id}/run` returns **202** `{workflow_id}`.
2. A background task runs the graph. After every node, state is saved. The UI polls `/workflow` every 2 seconds.
3. `human_approval` interrupts. The service writes `approval_requests` and sets the ticket to `waiting_on_approval`.
4. `POST /approvals/{id}/approve` or reject resumes the graph.
5. The tail is `execute_resolution` → `ticket_summary` → `memory_update` → END.
6. “Send reply” is a separate `POST /tickets/{id}/reply`.

## Acceptance for the whole project

- Every `F` and `N` row above has at least one test.
- `make test` passes with no network and no API key.
- `make demo` pauses on `CD-1002` and escalates `CD-1005` by rule.
- `CD-1013` does not export records and does not change the route the graph takes.
- Viewer tokens receive 403 on run, reply, and approve.
- `docker compose config -q` succeeds.
- `MEMORY.md` still says cloud apply and GitHub execution have not happened, until they have.
- `README.md` matches §14 commands once that file exists.

## Risks to watch while building

- Two sources of ticket categories. The schema module is the only place a category is introduced.
- Model-written tool calls. Actions stay on the deterministic plan.
- Side effects before `interrupt()`, which re-run on resume.
- Reducer fields overwritten instead of appended, which drops `completed_nodes` and breaks the UI.
- Embedding changes without a reindex, which silently empties retrieval.
- Service-role key imported into the frontend.
- Calling a phase “deployed” because the Terraform files exist.

## Definition of done for any single change

- The requirement id is named in the test.
- The layer rules in `CLAUDE.md` §4.2 hold.
- Contract, backend schema, and `frontend/lib/types.ts` match if the HTTP shape changed.
- Offline tests for that area pass.
- The honest-status table is still true.
