# Architecture and verification contract

## Boundaries

The React/Vite client speaks HTTP to FastAPI. PostgreSQL or SQLite owns the
workspace state. An independent worker executes approved local tools. The browser
does not own jobs, model keys or approval policy. It polls for current state.

The v0.1 runtime deliberately uses database-backed jobs instead of adding Redis,
Celery and an agent graph before there are multi-step workflows. The model layer
is a replaceable adapter. LangGraph can later implement a multi-step runner behind
the same action boundary; the current version does not claim to use it.

Modules:

- `backend/dayloom/api.py`: authenticated HTTP boundary and explicit user actions.
- `db.py`: typed persistence and metadata-only audit records.
- `policy.py`: deterministic content hash and exact approval check.
- `planning.py`: rule baseline for priority, deadlines, capacity and free intervals.
- `worker.py`: claims, leases, recovery and local transactions.
- `registry.py`: decorator registration, module discovery and constructor injection.
- `providers/`, `tools/`, `connectors/`: independently registered implementations.
- `apps/web`: client, browser tests and Capacitor configuration.

## Action lifecycle

`pending -> queued -> running -> succeeded | failed`

User approval records a SHA-256 digest of canonical tool name and validated
payload. Editing a pending/queued/failed action clears approval and returns it to
pending. A failed action can be retried only after returning to review. Cancellation
is supported before execution; running database transactions are not interrupted.

The worker claims jobs with a conditional update and a lease, then verifies the
approved hash again. Current tools and success records commit in one transaction.
An abandoned lease can be reclaimed; recovery attempts are bounded. The initial
release supports one worker per SQLite database. PostgreSQL is the scale-up path.

Do not add network side effects inside these database transactions. A sending or
publishing tool needs durable intent, provider idempotency keys, uncertain-outcome
reconciliation and approval bound to the exact recipient and body. A browser agent
also needs isolation, credential brokering, resource budgets and human takeover.

## Data contracts

Task status is user-work status; action status is AI-execution status. They are
different objects. A task is never marked done just because a model said so.
Memory has content, source, category, version and optional expiry. Expired memory
is excluded from model context. User edits are the source of truth.

The database is authoritative. JSON exports are portable snapshots, not a second
live database. Markdown import/export and semantic indexing are follow-ups.
Deleting a memory is not deleting all source evidence: chats and action history
remain unless the entire workspace is erased. Backups have independent retention.

## First acceptance gates

| Slice | Baseline/check | Pass condition |
| --- | --- | --- |
| Planning | Deadline/priority rule baseline, identical input | No event overlap or capacity overflow; no past blocks |
| Approval | Before/after payload mutation | Old approval never executes changed content |
| Recovery | Expired worker lease | One local effect and a persisted result |
| Retry | Failure to review to fresh approval | No retry without renewed approval |
| Memory | CRUD, expiry and model-context capture | Deleted/expired record absent from active memory context |
| Calendar | Repeated and malformed ICS imports | No duplicates; failed import preserves previous snapshot |
| Security | Token checks, hostile origins, preflight | Protected requests reject; allowed native preflight works |
| Client | Desktop/mobile browser flows | CRUD, proposal approval, execution visibility, no horizontal overflow |

Future model experiments must first run the same-input rule baseline and define
the comparison matrix. Do not call a model plan better based on different data,
budgets or evaluators. Remote model quality is not certified by the offline suite.

## Roadmap

1. OAuth read-only connector and explicit source revocation.
2. Follow-up objects, event triggers, recurring schedules and notification budgets.
3. Migration tooling, per-user identity and robust offline conflict resolution.
4. Native secure storage, sharing, calendar and push adapters.
5. Multi-step runner and isolated browser execution after effect-safety tests exist.