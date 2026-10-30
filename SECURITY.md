# Security boundaries

This is an early, single-user, self-hosted application. Do not expose it to
untrusted networks without a configured access token and an HTTPS reverse proxy.
The development server binds to loopback. It is not an authentication gateway.

## Credentials

Keep model keys and access tokens in local environment configuration. They are
excluded from source control and are not returned by the settings API. Do not
put them in frontend build variables, URLs, screenshots or issue reports.
Rotate any key shared in chat immediately. Never commit a real `.env` file.

The current access model is one workspace token, not per-user accounts. Web
tokens live only in sessionStorage. XSS can read them; do not install untrusted
frontend plugins. Native distribution needs secure storage and scoped sessions.
The model URL is administrator-controlled. It is not an arbitrary user-supplied
proxy. Configure a trusted HTTPS endpoint, or loopback for a local model.

## Model and action safety

Remote model use requires explicit client consent and server-side checking of
that consent. Context is minimized and bounded. Model output is schema validated
and can propose only registered tools. Imported content cannot confer authority.
Every model-created action requires approval; the worker rechecks exact content.
Tool credentials, payment capabilities and arbitrary shell/browser execution are
not exposed in v0.1. Do not add them without separate security review.

## Persistence and retention

Local database files are not encrypted by Dayloom. Protect the host, filesystem
permissions and backups; use disk encryption where appropriate. Reverse proxies
provide transport TLS. External model providers have their own retention policies.
Self-hosting alone does not mean model context stays on your machine.

Deleting a memory deletes that active memory record. Its original chat or approved
action may still exist and can be part of recent conversation context. The app
does not claim complete erasure from a single memory-delete operation. Workspace
deletion removes application records, but not backups or external-provider data.
Audit events store identifiers and action metadata, not copies of memory content.

Current execution guarantees apply to short local database operations with one
SQLite worker. Network effects require provider-specific idempotency, confirmation
and outcome reconciliation. A lease is not an exactly-once delivery guarantee.

## Reporting

Do not post tokens or private workspace exports in issues. If this repository is
made public, enable GitHub private vulnerability reporting before accepting
security reports. Contact the repository owner privately for sensitive findings.