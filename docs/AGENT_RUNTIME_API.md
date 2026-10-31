# Specialist Agent Runtime API

All routes require the existing admin authentication unless noted otherwise.

## Runtime lifecycle

The application creates `agent_tasks`, `agent_task_steps`, and `agent_approvals`
during startup. The runtime is deliberately bounded: model responses are data only.
They cannot invoke tools, execute plans, contact businesses, publish listings, quote,
contract, purchase, or move money.

## Endpoints

- `GET /agent-work/roles` — list specialist roles and allow/deny boundaries.
- `POST /agent-work/tasks` — enqueue a task with a JSON payload and 1–8 unique roles.
- `POST /agent-work/tasks/{id}/run` — run the queued task once.
- `POST /agent-work/tasks/{id}/cancel` — cancel a task only while it remains queued.
- `GET /agent-work/tasks/{id}` — inspect task, steps and approval ledger.
- `POST /agent-work/tasks/{id}/approval-requests` — record an approval request; does not execute it.
- `POST /agent-work/approvals/{id}/decision` — record a decision.

## Approval credential

Set a dedicated high-entropy `AGENT_APPROVER_TOKEN` in the hosting environment.
Do not reuse `ADMIN_TOKEN`. Approval decisions require both authenticated admin access
and `X-Approver-Id` plus the matching `X-Approver-Token`. The identity header is an
audit label; the separate secret is the authorization check. Rotate this secret if exposed.

An approved decision is only a ledger record. This runtime intentionally has no action
executor, so approval does not send a message or cause another external side effect.
A future action executor must validate the approval record, exact action payload hash,
expiry, scope, target, and one-time use server-side before acting.

## Execution behavior

- Roles are allowlisted from `app/agent_roles.py`; unknown or duplicate roles are rejected.
- A task can be claimed only once from `queued` to `running`; queued tasks may be cancelled before execution.
- Each step stores input hash, prompt hash, provider status and output.
- Provider failures become `INSUFFICIENT_EVIDENCE`; they are not silently treated as success.
- Model disagreements remain visible in separate outputs.
- Compliance `BLOCKED` halts downstream roles.
- No configured AI key means no model calls and a clear insufficient-evidence result.
- No search API, email provider, or paid service is activated by this runtime.

## Launch requirements not yet implemented

This is a controlled execution foundation, not a production-grade agent platform yet.
Before enabling broader autonomous workloads, add: per-user marketplace authorization,
rate limits and quotas for agent-work routes, task cancellation and lease recovery,
retention/deletion controls, schema-versioned output validation, independent legal
screening integrations, human-reviewed identity/transaction workflows, and adversarial
integration tests. The current approver token is a single shared secret, not individual
SSO/MFA or non-repudiation. A human operator and qualified counsel remain necessary.
