# CloudDesk - API Contract

Source of truth for every HTTP route and type. If an endpoint changes, update this file,
`backend/app/schemas/` and `frontend/lib/types.ts` in the **same change** (`CLAUDE.md` §12).

**Status:** draft v0, written before implementation. Route groups, status codes, enums and the
`Evidence` shape come from `CLAUDE.md`. Field lists marked *(draft)* are a starting proposal -
confirm or change them in Phase 4 and remove the marker.

---

## 1. Conventions

- Base path: `/api/v1`. Health routes are unprefixed.
- Auth: `Authorization: Bearer <JWT>` (HS256). Missing/invalid → `401`. Role too low → `403`.
- Every response carries `X-Request-ID` (echoed if the client sent one, generated otherwise).
- Errors: `{ "detail": string }` with the proper status code.
- Times: ISO-8601 UTC strings. IDs: UUID strings (`String(36)`), except ticket `number` like `CD-1002`.
- Lists: `{ "items": T[], "total": number }`, query `?limit=` (default 50, max 200) and `?offset=`.
- Rate limit: `429` with `Retry-After` when `RATE_LIMIT_PER_MINUTE` is exceeded.
- Role column: minimum role required. `public` = no token.

---

## 2. Enums

```ts
type Role       = "viewer" | "agent" | "admin";
type Category   = "login_issue" | "billing" | "api_failure" | "workspace_permissions"
                | "storage_quota" | "integration" | "feature_request" | "account"
                | "security" | "other";
type Severity   = "low" | "medium" | "high" | "critical";
type TicketStatus = "new" | "in_progress" | "waiting_on_customer" | "waiting_on_approval"
                  | "escalated" | "resolved" | "closed";
type Channel    = "email" | "chat" | "web" | "api";
type Plan       = "free" | "pro" | "business" | "enterprise";
type RiskLevel  = "low" | "medium" | "high";
type RunStatus  = "queued" | "running" | "paused" | "completed" | "failed";        // (draft)
type ApprovalStatus = "pending" | "approved" | "rejected";
type MemoryKind = "preference" | "past_issue" | "troubleshooting" | "note";
type RetrievalMode = "hybrid" | "semantic" | "keyword";
type EventType  = "node_started" | "node_completed" | "tool_called" | "llm_called"
                | "approval_requested" | "approval_resolved" | "error" | "workflow_completed";
type NodeId     = "understand_ticket" | "classify_severity" | "customer_context"
                | "knowledge_retrieval" | "troubleshooting" | "resolution_planning"
                | "risk_check" | "human_approval" | "execute_resolution" | "escalation"
                | "ticket_summary" | "memory_update";
```

---

## 3. Shared types

```ts
interface User { id: string; email: string; name: string; role: Role }

interface Ticket {                                   // (draft)
  id: string; number: string;                        // "CD-1002"
  subject: string; body: string; channel: Channel;
  status: TicketStatus; category: Category | null; severity: Severity | null;
  customer_id: string; assignee_id: string | null;
  created_at: string; updated_at: string;
}

interface TicketMessage {                            // (draft)
  id: string; ticket_id: string;
  author_type: "customer" | "agent" | "system"; author_name: string;
  body: string; created_at: string;
}

interface Customer {                                 // (draft)
  id: string; name: string; email: string; company: string; plan: Plan; created_at: string;
}
interface Subscription { id: string; customer_id: string; plan: Plan; seats: number;
  seats_used: number; status: string; renews_at: string | null }          // (draft)
interface Workspace { id: string; customer_id: string; name: string;
  storage_used_gb: number; storage_quota_gb: number }                     // (draft)
interface MemoryNote { id: string; customer_id: string; kind: MemoryKind;
  content: string; created_at: string }

interface Evidence {
  id: string; title: string;
  source: string;            // "kb://<slug>#<section>"
  snippet: string; score: number;
  url: string;               // "/knowledge/<id>"
  article_id: string;
}
interface PreviousCase { ticket_number: string; subject: string; resolution: string; similarity: number }

interface Classification { category: Category; summary: string; confidence: number }
interface SeverityAssessment { severity: Severity; reason: string; raised_by_rule: boolean }
interface Diagnosis { probable_causes: string[]; steps: string[] }       // steps are ordered
interface PlannedAction {
  id: string; tool: string; args: Record<string, unknown>;
  requires_approval: boolean; status: "planned" | "executed" | "failed" | "skipped";
}
interface ResolutionPlan {
  summary: string; customer_reply: string; internal_notes: string;
  actions: PlannedAction[]; citations: string[];  // Evidence ids
}
interface EscalationDecision {
  escalation_required: boolean; team: string | null; reason: string;
  policy_rule: string | null;    // set when a rule decided it
}
```

---

## 4. Routes

### 4.1 Health (unprefixed)

| Method | Path | Role | Response |
|---|---|---|---|
| GET | `/health` | public | `{ status: "ok", version: string }` |
| GET | `/health/live` | public | `{ status: "ok" }` - no I/O, used by probes |
| GET | `/health/ready` | public | `{ status: "ok" \| "degraded", checks: { db, redis, vector_store, llm: "ok" \| string } }`; `503` when not ready |

### 4.2 Auth

| Method | Path | Role | Body | Response |
|---|---|---|---|---|
| POST | `/auth/login` | public | `{ email }` (demo users only) | `{ access_token, token_type: "bearer", expires_in: 28800, user: User }` |
| GET | `/auth/me` | viewer | - | `User` |

Demo login only works when `DEMO_MODE=true`. In cloud, tokens are issued by Supabase and only
verified here.

### 4.3 Dashboard

| Method | Path | Role | Response |
|---|---|---|---|
| GET | `/dashboard/summary` | viewer | `{ open_tickets, waiting_on_approval, escalated, resolved_today, by_category: Record<Category, number>, by_severity: Record<Severity, number>, metrics: { resolved_without_edit_pct, median_first_response_minutes, escalation_precision, refund_approvals_this_week } }` *(draft)* |

### 4.4 Tickets

| Method | Path | Role | Body / query | Response | Errors |
|---|---|---|---|---|---|
| POST | `/tickets` | agent | `{ subject, body, channel, customer_email }` | `201 Ticket` | 404 unknown customer, 422 |
| GET | `/tickets` | viewer | `?status&category&severity&customer_id&q&limit&offset` | `List<Ticket>` | |
| GET | `/tickets/{id}` | viewer | `{id}` = UUID or `CD-xxxx` | `Ticket & { messages: TicketMessage[] }` | 404 |
| POST | `/tickets/{id}/run` | agent | - | `202 { workflow_id }` | 404; **409** if `waiting_on_approval` or a run is active |
| GET | `/tickets/{id}/workflow` | viewer | - | `WorkflowRun \| null` | 404 |
| GET | `/tickets/{id}/events` | viewer | `?workflow_id` (default latest) | `WorkflowEvent[]` | 404 |
| POST | `/tickets/{id}/reply` | agent | `{ body }` | `TicketMessage`; ticket → `waiting_on_customer` or `resolved` *(draft)* | 404, **422** if output validation fails |
| POST | `/tickets/{id}/request-info` | agent | `{ body }` | `TicketMessage`; ticket → `waiting_on_customer` | 404 |
| POST | `/tickets/{id}/escalate` | agent | `{ team, reason }` | `Escalation`; ticket → `escalated` | 404 |

```ts
interface WorkflowRun {
  id: string; ticket_id: string; thread_id: string; status: RunStatus;
  current_node: NodeId | null; completed_nodes: NodeId[];
  classification: Classification | null; severity: SeverityAssessment | null;
  customer_context: { customer: Customer; subscription: Subscription | null;
                      workspace: Workspace | null; previous_tickets: Ticket[];
                      memory: MemoryNote[] } | null;
  evidence: Evidence[]; similar_cases: PreviousCase[];
  diagnosis: Diagnosis | null; resolution_plan: ResolutionPlan | null;
  risk_level: RiskLevel | null; escalation: EscalationDecision | null;
  approval_id: string | null; approval_status: ApprovalStatus | null;
  injection_detected: boolean;
  token_usage: { input_tokens: number; output_tokens: number; estimated_cost_usd: number };
  errors: string[]; started_at: string; finished_at: string | null;
}                                                                            // (draft)

interface WorkflowEvent {
  id: string; workflow_id: string; type: EventType; node: NodeId | null;
  name: string | null;               // tool name or LLM purpose ("diagnosis")
  duration_ms: number | null;
  input_tokens: number | null; output_tokens: number | null; cost_usd: number | null;
  payload: Record<string, unknown>;  // never raw prompts, secrets or other customers' data
  created_at: string;
}
```

### 4.5 Approvals

| Method | Path | Role | Body | Response | Errors |
|---|---|---|---|---|---|
| GET | `/approvals` | viewer | `?status=pending` | `List<ApprovalRequest>` | |
| GET | `/approvals/{id}` | viewer | - | `ApprovalRequest` | 404 |
| POST | `/approvals/{id}/approve` | agent | `{ note? }` | `ApprovalRequest`; resumes graph | 404, **409** if not pending / run not paused |
| POST | `/approvals/{id}/reject` | agent | `{ note }` | `ApprovalRequest`; resumes graph → escalation | 404, **409** |

```ts
interface ApprovalRequest {
  id: string; ticket_id: string; workflow_id: string;
  actions: PlannedAction[]; reason: string; status: ApprovalStatus;
  decided_by: string | null; decided_at: string | null; note: string | null; created_at: string;
}
```

### 4.6 Customers

| Method | Path | Role | Response |
|---|---|---|---|
| GET | `/customers` | viewer | `List<Customer>` (`?plan&q`) |
| GET | `/customers/{id}` | viewer | `Customer & { subscription, workspaces: Workspace[], tickets: Ticket[], memory: MemoryNote[] }` |

### 4.7 Knowledge

| Method | Path | Role | Body / query | Response |
|---|---|---|---|---|
| GET | `/knowledge` | viewer | - | `List<{ id, slug, title, category, tags: string[], summary }>` |
| GET | `/knowledge/{id}` | viewer | - | article + `content` (markdown) |
| POST | `/knowledge/search` | viewer | `{ query, mode?: RetrievalMode, category?, top_k?: number (default 5) }` | `{ results: Evidence[], mode, took_ms }` |
| POST | `/knowledge/reindex` | **admin** | - | `{ articles: number, chunks: number, collection: string }` - recreates the collection |

### 4.8 Escalations

| Method | Path | Role | Response |
|---|---|---|---|
| GET | `/escalations` | viewer | `List<Escalation>` (`?team&status`) |

```ts
interface Escalation { id: string; ticket_id: string; team: string; reason: string;
  policy_rule: string | null; status: "open" | "acknowledged" | "closed"; created_at: string }  // (draft)
```

### 4.9 Agents

| Method | Path | Role | Response |
|---|---|---|---|
| GET | `/agents` | viewer | `{ agents: { name, nodes: NodeId[], tools: string[], description }[], nodes: GRAPH_NODES, edges: { from: NodeId, to: NodeId, condition?: string }[] }` |

### 4.10 Audit

| Method | Path | Role | Response |
|---|---|---|---|
| GET | `/audit` | viewer | `List<{ id, request_id, user_email, method, path, status_code, created_at }>` (`?user&path&since`) |

### 4.11 Settings

| Method | Path | Role | Body | Response |
|---|---|---|---|---|
| GET | `/settings` | viewer | - | non-secret runtime settings: `{ demo_mode, environment, llm_provider, llm_model, vector_store, embedding_model, approval_required_for_refunds, max_refund_without_approval, rate_limit_per_minute }` |
| PATCH | `/settings` | **admin** | subset of the editable flags *(draft: which flags are editable at runtime)* | same as GET |

Never returns keys, secrets, or connection strings.

### 4.12 MCP

| Method | Path | Role | Response |
|---|---|---|---|
| GET | `/mcp/tools` | viewer | `{ tools: { name, description, requires_approval, writes: boolean }[] }` - the MCP server (`make mcp`) exposes read-only tools only |

---

## 5. Role matrix (must be tested)

| Action | viewer | agent | admin |
|---|---|---|---|
| Read anything under §4 | ✓ | ✓ | ✓ |
| Create ticket, run, reply, request-info, escalate | 403 | ✓ | ✓ |
| Approve / reject | 403 | ✓ | ✓ |
| Reindex knowledge, PATCH settings | 403 | 403 | ✓ |

## 6. Change log

| Date | Change |
|---|---|
| 2026-10-25 | Draft v0 created from `CLAUDE.md`. |
