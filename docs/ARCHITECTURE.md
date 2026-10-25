# CloudDesk - Architecture

Component and infrastructure view of the Autonomous Customer Support & Resolution Platform.
`CLAUDE.md` §4 is the spec; this file expands it with diagrams. If they disagree, `CLAUDE.md` wins.

**Status:** design only. Nothing below is implemented yet (see `MEMORY.md` honest status).

---

## 1. System context

```text
                ┌────────────────────┐
 Support agent ─▶  Agent console     │  Next.js 15 (:3000)
 (viewer/agent/ │  frontend/         │  bearer JWT in localStorage
  admin)        └─────────┬──────────┘
                          │ REST /api/v1  (Authorization: Bearer, X-Request-ID)
                ┌─────────▼──────────┐
                │  FastAPI backend   │  (:8000)
                │  backend/app/      │
                │  ┌──────────────┐  │
                │  │ LangGraph    │  │  agents/graph.py
                │  │ workflow     │  │  6 specialists + rules + tools
                │  └──────────────┘  │
                └──┬──────┬──────┬───┴──────────┬──────────────┐
                   ▼      ▼      ▼              ▼              ▼
             Postgres  Redis   Qdrant      LLM provider    Mock integrations
             /SQLite   /fake   /in-memory  (get_llm)       (billing, status,
                                            + LangSmith     workspace admin)
```

Customers never touch the system in v1. Tickets arrive through `POST /api/v1/tickets` (email, chat,
web, api channels - all mocked).

---

## 2. Backend components

```text
backend/app/
  main.py ─ setup_logging, middleware, lifespan(create_tables, bootstrap_demo_data)
  middleware/   CORS → RequestId → RateLimit → Audit   (outermost last)
  api/          routers (auth, tickets, approvals, customers, knowledge, escalations,
                agents, audit, settings, dashboard, mcp, health)
      │ calls
  services/     workflow_service · approval_service · ticket_service · seed_service · ...
      │ calls                         │ starts / resumes
  repositories/ (SQLAlchemy)          agents/graph.py
      │                                   │ nodes call
  models/entities.py                  agents/specialists/*  ── agents/rules.py
                                          │                    agents/prompts.py
                                          ├─ core/llm.py  call_structured → get_llm()
                                          ├─ tools/  ToolRegistry.execute ─ ToolPolicy
                                          │            └─ integrations/ (Protocols + mocks)
                                          ├─ rag/retriever.py
                                          └─ memory/memory_service.py
  core/  config · llm · security · logging · redis · guardrails · observability · database
```

Dependency direction is top-down only. `core` imports nothing from `agents/` or `integrations/`.
See the layering table in `CLAUDE.md` §4.2.

---

## 3. Workflow graph

```text
START
  │
understand_ticket ─▶ classify_severity ─▶ customer_context ─▶ knowledge_retrieval
  │
troubleshooting ─▶ resolution_planning ─▶ risk_check
                                             │
             ┌───────────────────────────────┼─────────────────────────┐
     escalation_required            approval pending                 low risk
             │                               │                         │
             ▼                         human_approval (interrupt)      │
         escalation ◀── rejected ──────────┤                           │
             │                         approved                        │
             │                               ▼                         │
             │                       execute_resolution ◀──────────────┘
             ▼                               │
       ticket_summary ◀──────────────────────┘
             │
       memory_update ─▶ END
```

| Node | Agent | Writes to state |
|---|---|---|
| `understand_ticket` | Supervisor | `classification`, `injection_detected` |
| `classify_severity` | Supervisor | `severity` |
| `customer_context` | Customer | `customer_context` (incl. memory notes) |
| `knowledge_retrieval` | Knowledge | `evidence`, `similar_cases` |
| `troubleshooting` | Troubleshooting | `diagnosis`, `service_status` |
| `resolution_planning` | Resolution | `resolution_plan`, `output_validation` |
| `risk_check` | Escalation | `risk_level`, `escalation_decision` |
| `human_approval` | - | `approval_status` |
| `execute_resolution` | - | `action_results` |
| `escalation` | Escalation | `escalation` |
| `ticket_summary` | Supervisor | `summary` |
| `memory_update` | - | (writes `customer_memory`) |

State fields beyond `completed_nodes`, `errors` and `token_usage` are working names; the
authoritative definition is `agents/state.py` once written.

### 3.1 Run and approval sequence

```text
UI              API                 workflow_service        Graph            DB
│ POST /run ───▶│ create_run ───────▶│ insert workflow_runs ─────────────────▶│
│◀── 202 ───────│                    │                                        │
│               │ BackgroundTasks ──▶│ start_workflow ─▶ astream              │
│ GET /workflow │ (every 2 s)        │   save state after every node ────────▶│
│               │                    │                 human_approval         │
│               │                    │◀─ interrupt ─── (checkpoint thread_id) │
│               │                    │ _handle_interrupt: approval_requests, ─▶│
│               │                    │   ticket=waiting_on_approval           │
│ POST /approvals/{id}/approve ─────▶│ approval_service.decide                │
│               │                    │ resume_workflow(Command(resume=…)) ─▶  │
│               │                    │   execute_resolution → summary → memory│
│ POST /reply ─▶│ (separate, agent-initiated)                                 │
```

---

## 4. Data stores

| Store | Demo | Cloud | Holds |
|---|---|---|---|
| Relational | SQLite `data/support.db` | Supabase Postgres | 16 tables (`CLAUDE.md` §6), workflow state as JSON |
| Checkpoints | `InMemorySaver` / `AsyncSqliteSaver` `data/checkpoints.db` | same file on a volume (v1) | paused graph state by `thread_id` |
| Cache / short-term memory | fakeredis | Redis | per-ticket conversation, rate-limit windows, `rag:*` cache (300 s) |
| Vectors | in-memory | Qdrant (`clouddesk_knowledge`) | knowledge chunks, 384-dim fake embeddings in demo |

---

## 5. Trust boundaries

```text
 ┌─ untrusted ───────────────┐      ┌─ trusted ─────────────────────────────┐
 │ ticket body, email, file, │──▶ scan_for_injection ─▶ wrap_untrusted ─▶ prompt (SECURITY_PREAMBLE)
 │ web content               │      │                                       │
 └───────────────────────────┘      │ model output ─▶ Pydantic schema       │
                                    │   ─▶ rules override (policy cases)    │
                                    │   ─▶ ToolPolicy (approval gate)       │
                                    │   ─▶ validate_customer_output ─▶ UI   │
                                    │   ─▶ scrub() ─▶ customer_memory       │
                                    └───────────────────────────────────────┘
```

- Browser holds only the anon key / a user JWT. The service-role key stays on the backend.
- Every non-GET request is audited; every node/tool/LLM call is a `workflow_events` row.

---

## 6. Deployment topology

```text
docker compose (local):   frontend ─▶ backend ─▶ redis, qdrant   (depends_on: service_healthy)

Cloud (same images, tag = git SHA):
                 ┌──────────── AWS ─────────────┬──────── Azure ────────┬───────── GCP ──────────┐
 Registry        │ ECR                          │ ACR                   │ Artifact Registry      │
 Compute         │ ECS Fargate                  │ Container Apps        │ Cloud Run              │
 Ingress         │ ALB                          │ built-in ingress      │ built-in HTTPS         │
 Secrets         │ Secrets Manager              │ Key Vault             │ Secret Manager         │
 Logs/metrics    │ CloudWatch                   │ Log Analytics         │ Cloud Logging          │
 Redis           │ ElastiCache                  │ Azure Cache for Redis │ Memorystore            │
                 └──────────────────────────────┴───────────────────────┴────────────────────────┘
 External on every cloud: Supabase (Postgres + auth), Qdrant Cloud, LLM API, LangSmith (optional)
```

Terraform: `deployment/{aws,azure,gcp}` roots over shared modules (networking, container-registry,
secrets, compute, load-balancer, monitoring, redis); environments are var-files. CI/CD in
`CLAUDE.md` §15. The managed-Redis service names in the table are the obvious mapping and are not
yet fixed by `CLAUDE.md`; confirm when the `redis` module is written.
