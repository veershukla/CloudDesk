**Git & GitHub Workflow Guide**

CloudDesk — Autonomous Customer Support & Resolution Platform

*Version 1.0  \|  Last updated: October 23, 2026*

|  |  |
|---|---|
| Audience | Contributors: backend, frontend, RAG, infra, and QA |
| Repository | https://github.com/anulsasidharan/CloudDesk.git |
| GitHub account | anulsasidharan |
| Default integration branch | development |
| Long-lived branches | development, testing, main |
| Task tracker | TASKS.md — one feature/\<name\> branch per sub-task |
| Remote status | Empty as of October 23, 2026. No commits have been pushed. |

This guide is how code moves for CloudDesk. Feature work branches from development and merges back through a pull request. testing and main are promotion branches for staging and production. Follow it so main stays releasable and every sub-task in TASKS.md has one reviewable branch.

# Contents

- 1. Branch model at a glance
- 2. Before you start
- 3. First-time setup
- 4. Daily workflow (feature → development)
- 5. Pull requests
- 6. Promoting code: development → testing → main
- 7. Branch naming
- 8. CloudDesk checks before you open a PR
- 9. Quick reference
- 10. Questions

# 1. Branch model at a glance

Three long-lived branches. Day-to-day work targets development only. The GitHub repository is empty until the first push, so main, development, and testing do not exist there yet. Section 3 creates them. After that, do not recreate them per feature.

| **Branch** | **Purpose** | **Who merges here** | **What it represents** |
|---|---|---|---|
| development | Integration branch for active work | Contributors, via a PR from feature/\* or bugfix/\* | Dev / integration. Not a production deploy. |
| testing | QA and staging validation | Release owner | Staging. Apply still needs a reviewed plan. |
| main | Code that is allowed to ship | Release owner | Production candidate. A merge is not itself a deploy. |

**Rules**

- Create every feature branch from an up-to-date development.
- Open every feature pull request into development. Do not open it into testing or main.
- Do not push commits directly to development, testing, or main.
- Do not stack a feature branch on another feature branch. If TASKS.md names a predecessor, merge that predecessor first.
- One sub-task in TASKS.md is one branch, one pull request, and one status change to Completed ✅ after merge.
- A merge to main does not mean the cloud environment is deployed. MEMORY.md stays honest until a real apply has happened.

# 2. Before you start

## Access

- Use the GitHub account that owns https://github.com/anulsasidharan/CloudDesk. Collaborators need write access before they can push.
- Confirm the repository page loads. As of October 23, 2026 it has no commits.
- Turn on two-factor authentication on the GitHub account.
- Prefer HTTPS with GitHub CLI, or SSH if you already have a key on the account. Do not put tokens in the repo.

## Tools to install

| **Tool** | **Version** | **Notes** |
|---|---|---|
| Git | 2.40+ | Git for Windows includes Git Bash. PowerShell is the shell used in this project. |
| GitHub CLI (gh) | Latest | Recommended for pull requests from the terminal. |
| Python | 3.12 | Backend, agents, RAG, and pytest. Use .venv\\Scripts\\python.exe. |
| Node.js | 22 | Next.js 15 console. Frontend image uses node:22-alpine. |
| Docker | Current | Compose stack: frontend, backend, redis, qdrant. |
| Editor | Cursor or VS Code | Python, TypeScript, and Docker extensions. |

**Verify:**

```
git --version
gh --version
python --version
node --version
docker --version
```

## Read first

Read these before the first feature branch. CLAUDE.md wins if another file disagrees with it.

| **Document** | **Why** |
|---|---|
| CLAUDE.md | Specification: layers, domain, tools, workflow, and what must never happen. |
| TASKS.md | The sub-task you are doing, its feature/\<name\> branch, and Pending ❌ or Completed ✅. |
| PLAN\_PHASE.md | Exit criteria, tests, and the demo checkpoint for the phase. |
| PLAN.md | Requirement catalog F1–F14 and N1–N8. |
| MEMORY.md | Locked decisions and honest status. Update it when status changes. |
| docs/ARCHITECTURE.md | Component and infrastructure diagrams. |
| .cursor/skills/clouddesk-support/SKILL.md | How to implement a change in this repo. |
| docs/API\_CONTRACT.md | Route and payload shapes. Create it with the first API change. It does not exist yet. |

# 3. First-time setup

The GitHub repository is empty. The working copy on disk already has the specification files (CLAUDE.md, TASKS.md, PLAN.md, PLAN\_PHASE.md, MEMORY.md, docs/ARCHITECTURE.md, and this guide). Connect that copy to the remote, then create the three long-lived branches. Do this once.

## Configure your identity (once per machine)

Use the same email as the GitHub account so commits attach to the profile.

```
git config --global user.name "Your Full Name"
git config --global user.email "you@example.com"
```

## Seed the empty remote

From the project directory, in PowerShell. Skip git init if the folder is already a repository.

```
cd C:\Users\anuls\Videos\Euron_AgenticAI1.0
git init
git checkout -b main
git add CLAUDE.md MEMORY.md PLAN.md PLAN_PHASE.md TASKS.md docs .cursor/skills Git_GitHub_Workflow_Guide.docx
git status
git commit -m "docs: add CloudDesk specification and git workflow"
git remote add origin https://github.com/anulsasidharan/CloudDesk.git
git push -u origin main
git checkout -b development
git push -u origin development
git checkout main
git checkout -b testing
git push -u origin testing
git checkout development
```

Before that first commit, git status must not list any of these:

- .env, credentials, or any real API key
- data/, \*.db, or checkpoints
- terraform.tfvars, backend.hcl, or tfplan
- The service-role key

SSH remote, if you use keys:

```
git remote add origin git@github.com:anulsasidharan/CloudDesk.git
```

## Clone later, after the remote has commits

```
git clone https://github.com/anulsasidharan/CloudDesk.git
cd CloudDesk
git fetch origin
git checkout development
git pull origin development
```

Optional GitHub CLI login:

```
gh auth login
```

Choose HTTPS or SSH and finish in the browser. gh auth login does not store a token in the repository.

## Local runtime, after the code exists

These commands matter from Phase 1 onward. They are not required to push the specification.

```
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
$env:PYTHONPATH = "backend"
$env:PYTHONIOENCODING = "utf-8"
Copy-Item .env.example .env
```

DEMO\_MODE=true, LLM\_PROVIDER=fake, VECTOR\_STORE=memory, and USE\_FAKE\_REDIS=true are the offline defaults. Tests must pass with no API key. get\_settings() is cached, so restart the server after an .env change.

# 4. Daily workflow (feature → development)

Use this cycle for every row in TASKS.md. Start with P1-1 on feature/backend-config-logging. Phases 4, 5, 6, and 7 can run in parallel only after their listed predecessors are on development.

## Step 1 — Sync development

```
git checkout development
git pull origin development
```

## Step 2 — Create the feature branch

Copy the branch name from the TASKS.md row. Do not invent a second name for the same sub-task.

```
git checkout -b feature/backend-config-logging
```

Examples from the tracker:

- feature/backend-config-logging — P1-1 settings and JSON logging
- feature/sqlalchemy-entities — P2-1 entities and the ten ticket categories
- feature/api-tickets — P4-2 create and read tickets
- feature/rag-hybrid-retriever — P5-3 hybrid retrieval
- feature/tool-registry-policy — P6-1 registry and approval policy
- feature/workflow-human-approval — P11-1 pause for a refund approval
- feature/frontend-ticket-actions — P13-3 approve, reject, reply, escalate

## Step 3 — Implement and commit

Keep commits small. One logical change per commit. Present tense. A scope helps.

```
git add backend/app/core/config.py backend/app/core/logging.py
git commit -m "feat(core): add settings and JSON logging with request id"
```

Message prefixes: feat, fix, docs, test, chore, infra.

- feat(api): accept tickets from email, chat, web, and API
- feat(workflow): pause CD-1002 until the refund is approved
- fix(guardrails): keep CD-1013 ticket text as data
- test(rag): expect the MFA article for the lockout query
- docs: record Phase 1 as validated locally in MEMORY.md

Name the requirement in the test (F1–F14 or N1–N8). Stay inside one layer from CLAUDE.md section 4.2. Policy stays in code: agents/rules.py and backend/app/tools/policy.py.

## Step 4 — Push and open a pull request

```
git push -u origin feature/backend-config-logging
```

On GitHub, set base development and compare the feature branch. Or:

```
gh pr create --base development --head feature/backend-config-logging `
  --title "feat(core): add settings and JSON logging" `
  --body "## Summary`n- Add offline settings and JSON logs.`n`n## Related task`n- TASKS.md: P1-1`n`n## Test plan`n- [ ] Health tests pass offline"
```

In PowerShell the backtick continues the line. In Git Bash use a backslash instead.

## Step 5 — Address review

```
git add backend/app/core/logging.py
git commit -m "fix(core): include workflow id on log lines"
git push
```

The open pull request updates with the push. Re-request review when the comments are addressed. Do not open a second pull request for the same sub-task.

## Step 6 — After the merge

```
git checkout development
git pull origin development
git branch -d feature/backend-config-logging
git fetch --prune
```

Set that TASKS.md row to Completed ✅ in a follow-up docs commit on the next branch, or in the same pull request if the tracker update is part of the sub-task. Delete the remote feature branch when GitHub offers it.

# 5. Pull requests

## Target branch

| **Your branch** | **Pull request base** |
|---|---|
| feature/\* | development |
| bugfix/\* | development |
| hotfix/\* | main, then backport to development and testing |
| development (promotion) | testing |
| testing (promotion) | main |

## Title

- feat(tickets): create a ticket from email, chat, web, or API
- fix(auth): return 403 when a viewer runs a workflow
- test(workflow): CD-1002 pauses and resumes after approval
- docs: add the Eraser architecture diagrams

## Description

```
## Summary
- What changed and why (1–3 bullets)
## Related task
- TASKS.md: P4-2 · Ticket API
- Requirement: F1
## Test plan
- [ ] make test
- [ ] make lint
- [ ] Viewer token still receives 403 on run, reply, and approve
- [ ] No .env, database, or cloud secret in the diff
## Screenshots / notes
- UI changes only. Say what you could not verify.
```

## Before requesting review

- development is merged into the feature branch if it moved during the work (git checkout feature/... ; git merge origin/development).
- make test passes offline. make lint passes.
- A frontend change also has npm run lint and npm run test -- --run, and the ticket flow was checked in the browser when a server exists.
- A route or payload change updates docs/API\_CONTRACT.md, backend/app/schemas/, and frontend/lib/types.ts together.
- A schema change adds a new database/migrations/000N\_\<name\>.sql file and updates the model and database/schema.sql. Applied migrations are not edited.
- The diff contains no .env, data/, \*.db, terraform.tfvars, backend.hcl, tfplan, or service-role key.
- MEMORY.md is updated when implementation, local validation, cloud credentials, or deploy state changed.

## After merge

- Delete the remote feature branch.
- Pull development before starting the next sub-task.
- Do not start a sub-task whose predecessor is still open.

# 6. Promoting code: development → testing → main

Promotion is a pull request between long-lived branches. It is not a feature branch. Feature authors do not merge into testing or main. A promotion pull request is not a cloud apply. deployment/scripts refuses --auto-approve for staging and prod. Production apply uses the GitHub Environment prod-apply with required reviewers, once those workflows exist. They do not exist yet.

## development → testing

When development is stable for the phase exit criteria and the team wants a staging candidate.

```
git checkout testing
git pull origin testing
# Pull request: base testing, compare development
```

**Checklist**

- CI on development is green. Until GitHub Actions have been executed, say that they have not run.
- make test, and make demo for CD-1002 and CD-1005 once those checkpoints exist.
- Migrations are additive and backward compatible.
- No secret is in the tree.

## testing → main

When staging behavior is accepted and a production candidate is intended. Merging main does not deploy.

```
# Pull request: base main, compare testing
```

**Checklist**

- QA notes for the phase demo are written down.
- Security workflow results are acceptable, or the workflow has not been run yet and the PR says so.
- Rollback is the previous git SHA image, once images exist. Image tags equal the git SHA.
- The prod var-file is not the dev var-file. Apply waits for a reviewed plan.

## Who does what

| **Action** | **Owner** |
|---|---|
| Feature or bugfix PR into development | The contributor doing the TASKS.md row |
| development → testing | Release owner |
| testing → main | Release owner |
| Cloud apply from a tested image | Release owner, after prod-apply review. Not done yet. |
| hotfix/\* from main | Release owner, then backport to development and testing |

# 7. Branch naming

| **Pattern** | **Use** | **Create from** | **Merge into** |
|---|---|---|---|
| feature/\<name\> | One TASKS.md sub-task | development | development |
| bugfix/\<name\> | A fix that is not a tracker row | development | development |
| hotfix/\<name\> | Urgent fix to released code | main | main, then backport |

**Naming rules**

- Lowercase words separated by hyphens: feature/api-tickets.
- Use the branch string from TASKS.md when the row already has one.
- Do not use feature/fix-bug-2, feature/wip, or a person's name.
- A hotfix name says the fault: hotfix/viewer-can-approve.

# 8. CloudDesk checks before you open a PR

Run the checks that exist for the phase you are in. Do not claim a later checkpoint.

| **Check** | **Command** | **When** |
|---|---|---|
| Backend tests | make test | Every phase, once the harness exists. Offline, no API key. |
| Lint | make lint | Python changes. |
| Frontend | npm run lint and npm run test -- --run | Files under frontend/. |
| Demo | make demo then make demo TICKET=CD-1005 | Once the workflow exists. CD-1002 must pause. CD-1005 must escalate by rule. |
| Compose | docker compose config -q | Delivery phase, when the compose file exists. |
| Smoke | BASE\_URL=http://localhost:8000 make smoke | Against a local stack only, until a real host exists. |

On Windows, put backend on PYTHONPATH with a semicolon and set PYTHONIOENCODING=utf-8. Call Python as .venv\\Scripts\\python.exe.

**Behavior that must remain true**

- A viewer receives 403 on run, reply, and approve.
- CD-1013 does not export customer records and does not change the graph route.
- A refund, deletion, or setting reset does not run without a recorded approval.
- A customer reply does not contain internal URLs, secrets, or another customer's data.
- Memory notes do not contain card numbers, keys, passwords, or raw ticket bodies.
- Ticket categories are introduced only in backend/app/schemas/common.py.

# 9. Quick reference

```
git checkout development
git pull origin development
git checkout -b feature/my-task
# work, commit, push
gh pr create --base development --head feature/my-task
# review, squash-merge
git checkout development
git pull origin development
git branch -d feature/my-task
```

Promotion, release owner only:

```
development  --PR-->  testing  --PR-->  main
```

main is the production candidate. Deploy is a separate, reviewed apply. Nothing is deployed today.

# 10. Questions

- Branch and release policy: this guide and the repository admin.
- Which sub-task to pick: TASKS.md. Respect the Depends-on line for that phase.
- Spec, layers, and safety rules: CLAUDE.md.
- Diagrams: docs/ARCHITECTURE.md.

If the shape of a change is unclear, open a draft pull request into development early.

*End of document*
