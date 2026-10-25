---
name: clouddesk-support
description: Procedure for building or changing the CloudDesk Autonomous Customer Support & Resolution Platform (FastAPI + LangGraph + Next.js). Use for any work in this repo - a new phase, a feature, a bug fix, an API change, an agent, a tool, RAG, memory, the console, tests, or delivery files.
---

# CloudDesk support platform - agent procedure

`CLAUDE.md` is the spec and wins every disagreement. This skill is the order of operations for
applying it. If this skill and `CLAUDE.md` disagree, fix this skill.

## 0. Orient (every task)

1. Read `MEMORY.md` → the honest-status table and locked decisions.
2. Read `PLAN_PHASE.md` → find the current phase (first one not `validated locally`). Work only inside
   it unless the user names something else.
3. Find the requirement id(s) (`F1`–`F14`, `N1`–`N8`) the task serves in `PLAN.md`. If none fits,
   stop and ask - every change maps to a requirement.
4. If the task touches HTTP, read `docs/API_CONTRACT.md` first.
5. Read the existing test for the area before changing behaviour.

## 1. Place the code in the right layer

| If the change is... | It goes in | It must not |
|---|---|---|
| HTTP route, validation, auth, RBAC | `backend/app/api/` | hold business rules |
| Orchestration of repos + graph | `backend/app/services/` | talk HTTP |
| SQL | `backend/app/repositories/` | call an LLM |
| Config, llm factory, security, guardrails, logging | `backend/app/core/` | import `agents/` |
| A side effect an agent can take | `backend/app/tools/` (+ `ToolPolicy`) | bypass `ToolRegistry` |
| Policy decision | `agents/rules.py` | depend on a model call |
| Agent reasoning | `agents/specialists/`, `agents/nodes/` | write SQL |
| Retrieval | `rag/` | know about tickets |
| Notes about a customer | `memory/` | store secrets |
| External system | `integrations/` (Protocol + mock) | be imported by `core` |
| UI | `frontend/` via `lib/api.ts` only | hold the service-role key |

Need a shortcut across layers? Stop and refactor instead.

## 2. Recipes

### Add or change an API route
1. Update `docs/API_CONTRACT.md`.
2. Update the Pydantic schema in `backend/app/schemas/`.
3. Update `frontend/lib/types.ts`.
4. Add the route with `require_role(...)` at the right level (`viewer` read, `agent` act, `admin` reindex/settings).
5. Tests in `tests/api/`: happy path, 404, and a `viewer` 403 for anything mutating.
All four files change in the same commit.

### Add a tool
1. `async` function with `@tool`; the docstring is the description the LLM/MCP sees.
2. Register it in `ToolRegistry`; set its approval bit in `ToolPolicy`. Money or account → approval.
3. Exceptions return `ToolResult(ok=False)`; respect `TOOL_TIMEOUT_SECONDS`.
4. If the Resolution Agent should use it, add it to `plan_actions` (deterministic). Never let the model invent it.
5. Unit test in `tests/unit/` for the policy bit and the failure path.

### Add a policy / escalation rule
1. Add to `ESCALATION_RULES` in `agents/rules.py` with a named team.
2. Rules win over the model; severity rules may only raise severity.
3. Test in `tests/unit/` and add an eval case to `datasets/eval_cases.json`.

### Add or change a specialist agent or node
1. Output is a Pydantic model in `backend/app/schemas/workflow.py`.
2. LLM calls only via `call_structured`; prompts in `agents/prompts.py` with `SECURITY_PREAMBLE`.
3. Ticket/email/file/web text goes through `wrap_untrusted`.
4. Node returns a **partial** dict; append to `completed_nodes` / `errors`, never overwrite.
5. Use the node shape from `CLAUDE.md` §7.3 (`tracer.node`, `record_tool_calls`, `record_llm`).
6. Nothing with side effects before `interrupt()`.
7. If node ids change, update `GRAPH_NODES` / `GRAPH_EDGES` and the frontend `WorkflowSteps`.
8. Test in `tests/agents/` with `LLM_PROVIDER=fake`.

### Add a category
1. Add it to `backend/app/schemas/common.py` first (the only source).
2. Then rules, prompts, `frontend/lib/types.ts`, eval cases.

### Change the database
1. New file `database/migrations/000N_<name>.sql` - never edit an applied one; never drop data without an explicit decision.
2. Update `backend/app/models/entities.py` (portable: JSON, `String(36)` UUIDs) and `database/schema.sql`.
3. Add RLS for new data tables in `database/rls_policies.sql` and an `updated_at` trigger.

### Change the knowledge base or embeddings
1. Articles in `sample_data/knowledge_base/*.md` with front-matter `title, category, tags, summary`.
2. `make ingest`. Embedding model change → `POST /knowledge/reindex` (admin).
3. Re-check `tests/rag/` and hit-rate@3 ≥ 0.75.

### Add an environment variable
Add it to `backend/app/core/config.py`, `.env.example` (placeholder only), and `CLAUDE.md` §10.1.
`tests/deployment` checks coverage.

## 3. Safety checks before you finish

Answer each with yes. If one is no, fix it before reporting done.

- [ ] Ticket text cannot change the workflow route (CD-1013 still contained).
- [ ] No refund, deletion, setting reset or dispute runs without a recorded approval.
- [ ] A `viewer` gets 403 on run, reply, approve, reject, escalate.
- [ ] Customer-facing text passes `validate_customer_output` (no internal URLs, secrets, other customers' data).
- [ ] Memory notes go through `scrub()`; no raw ticket bodies.
- [ ] Every policy claim in a reply cites a knowledge article.
- [ ] No secrets in code, logs, memory, or committed files (`.env`, `data/`, `*.db`, `terraform.tfvars`, `backend.hcl`, `tfplan`).
- [ ] Telemetry (`WorkflowTracer`) cannot break a run; raw prompts are not in `workflow_events`.

## 4. Verify

```bash
make lint
make test                     # offline, no API key, no Docker
make demo                     # CD-1002 pauses for approval (from Phase 10 on)
make demo TICKET=CD-1005      # escalates by rule
cd frontend && npm run lint && npm run test -- --run   # if frontend changed
```

Before `make` exists (Phase 1), say so - do not claim tests passed.
The eval thresholds in `CLAUDE.md` §13 fail the build; do not lower them to pass.

## 5. Record and report

1. When a phase's exit criteria pass, set its status in `PLAN_PHASE.md` and `CLAUDE.md` §19, and
   add a dated line to the honest-status table in `MEMORY.md`.
2. Record any new locked decision in `MEMORY.md` with the date and requirement id.
3. One change, one commit, one test. Branch from `development`
   (see `Git_GitHub_Workflow_Guide.md`); PRs target `development`.
4. Report using the four honest states: **implemented**, **validated locally**, **needs cloud
   credentials**, **deployed**. Never write "deployed" or "passes in CI" until it has happened.
   Say what is not done.
