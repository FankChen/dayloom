# Dayloom

A self-hosted personal action assistant. Capture a thought, turn it into a task,
plan around your calendar, and approve exactly what the assistant may do.

Dayloom is an independent project. It is not affiliated with Meta Muse or Today AI.
This repository starts private; publishing it is a separate owner decision.

## What works in v0.1

- A responsive workspace with Today, Inbox, Tasks, Memories, Activity and Settings.
- Persistent tasks with priorities, estimates, deadlines, status and optimistic edit checks.
- A deterministic daily planner that respects imported calendar events, capacity and local time.
- Editable memory with source labels, expiration, deletion and JSON export.
- A clearly labeled offline demo and an OpenAI-compatible chat-completions adapter.
- Proposed actions that require explicit approval of the exact payload.
- A separate worker with persisted jobs, leases, bounded recovery and audit records.
- Three local tools: create a task, save a memory, and prepare a daily brief.
- Recurring ICS calendar imports through a maintained calendar parser.
- SQLite for a single local user; PostgreSQL for the Docker deployment.
- Generated Capacitor Android and iOS source projects for native client development.

No model API key is required to try the offline demo. It uses simple rules, not an LLM.
It accepts a note as a candidate task, `remember: ...` as a candidate memory, and
`plan my day` as a candidate daily brief. It does not infer dates or split complex requests.
No demo records are silently inserted: choose **Load sample workspace** explicitly.

## Quick start

Requirements: Node.js 24 LTS (minimum 22.12), npm, uv, and Python 3.12.
Run the following from the repository root:

```bash
uv sync --locked --python 3.12
npm --prefix apps/web ci
npm run dev
```

Open http://127.0.0.1:5178. The launcher starts the API on 8078, the worker and
the frontend. All development listeners bind to loopback. Ctrl+C stops the launcher.
The database lives in the ignored `data/` directory. Do not commit it.

Use `DAYLOOM_DEV_WEB_PORT` and `DAYLOOM_DEV_API_PORT` to choose different ports.
Production build: `npm run build`. The API can serve the resulting static client.

## Connect a model

Create your local `.env` using `.env.example` as the field reference, and configure:

```dotenv
DAYLOOM_MODEL_PROVIDER=OpenAIProvider
DAYLOOM_MODEL_BASE_URL=https://api.openai.com/v1
DAYLOOM_MODEL_NAME=gpt-4.1-mini
DAYLOOM_MODEL_API_KEY=
```

Enter the key locally; never send it in chat or commit it. The model name is an
example, not a requirement. The configured API must support Chat Completions and
JSON object responses. Restart the service after changing server configuration.

The chat consent checkbox authorizes sending the current message, the last eight
messages, up to 20 active task titles and up to 25 active memories to that provider.
Model keys never reach the browser. The server does not expose a model-URL editor.
There is a request timeout, a bounded output size and at most five proposals per reply.
Invalid model output does not create actions. No live model call is made by tests.

## Self-host with PostgreSQL

Set `DAYLOOM_ACCESS_TOKEN` and `DAYLOOM_DB_PASSWORD` locally. Use a URL-safe database
password, such as a randomly generated hexadecimal value, because it is used in a
database URI. Compose refuses to start without these settings.

```bash
docker compose up --build -d
```

Open http://127.0.0.1:8000 and enter the workspace access token. The database is on
an internal Docker network and is persisted in a named volume. The worker waits
for the API to initialize the schema. Back up the database before upgrading.

Remote use requires an HTTPS reverse proxy, an explicit `DAYLOOM_ALLOWED_ORIGINS`
JSON array and an access token. Do not expose the unprotected development proxy.
This is a single-user workspace, not a tenant-isolated SaaS. Read [SECURITY.md](SECURITY.md).

## Development and verification

```bash
npm run check
npm test
cd apps/web
npx playwright install chromium
npm run test:e2e
```

Browser tests start an isolated service and database on ports 18878 and 18078;
they do not delete the normal development workspace. CI is configured to run
both desktop and mobile viewport tests. A mobile viewport test is not a native-device
test. See [docs/VERIFICATION.md](docs/VERIFICATION.md) for completed local checks
and explicitly unverified environments.

Model selection and new connectors/tools use class-name registries, module
discovery and constructor injection. Add a module with `@providers.register`,
`@connectors.register`, or `@tools.register`; do not add provider switches to API routes.
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for boundaries and extension rules.

## Mobile route

See [docs/MOBILE.md](docs/MOBILE.md). The web client is functional now. Capacitor
provides a path to native packages, not a promise of App Store readiness. Native
calendar access, push, share extensions and secure token storage remain follow-ups.
The current web manifest provides install metadata; offline execution is not implemented.

## Deliberate limits

- No automatic email sending, purchasing, OS notification scraping or browser agent.
- Calendar imports are snapshots covering the next 32 days, not live OAuth sync.
- Tasks can be marked blocked; automated follow-up rules and dependencies are not implemented.
- Planning is the rule baseline, not a measured model improvement or an optimizer.
- Memory deletion removes that memory record, not original chats/action payloads.
  Whole-workspace deletion removes application records, not backups or provider copies.
- The worker must stay online. Closing a browser is fine; shutting down its host is not.
- Current tools only perform short database-local operations, committed atomically
  with their results. External-effect tools need additional idempotency and reconciliation.
- Initial schema creation is included. Versioned database migrations must precede
  any schema-changing release beyond v0.1.

## License

Original code is MIT licensed. Third-party dependencies retain their own licenses.
The workspace bitmap and PNG web app icons are generated by `scripts/generate_assets.py`.
Native template assets, fonts and other notices are listed in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).