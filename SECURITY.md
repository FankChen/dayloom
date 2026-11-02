# Security boundaries

This is an early self-hosted application with an unreleased account profile.
LocalAccess and the included Compose profile remain single-workspace modes, not
public multi-user deployments. The development server binds to loopback and is
not an authentication gateway. See [docs/OPERATIONS.md](docs/OPERATIONS.md) for
the additional production-account gates; they have not all been verified locally.

## Credentials

Keep server secrets in protected environment/secret storage. Workspace model and
SMTP credentials submitted through Settings are purpose-bound and encrypted at
rest with Fernet, not KMS envelope encryption. Credentials are excluded from
source control and are not returned by configuration or export APIs. Do not
put them in frontend build variables, URLs, screenshots or issue reports.
Rotate any key shared in chat immediately. Never commit a real `.env` file.

LocalAccess retains the legacy workspace token in browser sessionStorage; XSS can
read it. OIDC account mode uses hashed, revocable opaque sessions, rotating refresh
tokens, HttpOnly cookies and a required custom CSRF header on cookie-authenticated
mutations. Production cookies require HTTPS. Native bridge source stores tokens
in Keychain/Keystore and uses a separate PKCE-bound callback ticket; device
validation is still required. Identity-provider backchannel logout is not implemented.

Model origins and SMTP hosts are administrator allowlisted. They are not an
arbitrary user-controlled proxy; do not approve untrusted/private-network hosts.
The local encryption key file is owner-only and ignored by Git. Account mode
requires an external key shared by API and worker; protect its backups separately.

## Model and action safety

Remote model use requires explicit client consent and server-side checking of
that consent. Context is minimized and bounded. Model output is schema validated
and can propose only registered tools. Imported content cannot confer authority.
Every model-created action requires exact-content approval or an explicitly
authorized finite, expiring schedule; the worker rechecks authority before effects.
SMTP credentials are never given to the model. SMTP acceptance is not delivery.
An ambiguous external result stops at `outcome_unknown` without automatic replay;
manual resolution is owner-reported, not independent provider verification.

The browser runner only reads approved public HTTPS pages. It requires a separate
authenticated, sandboxed process and enforced egress/private-address/DNS controls;
a proxy URL alone does not establish isolation. It has no authenticated browsing,
arbitrary clicks, checkout or shell capability. Purchasing is not implemented.

Android notification capture source is opt-in and source-selected, encrypted and
bounded locally; uploading an item is explicit. Sensitive-content filtering is
best-effort. iOS cannot read other apps' notifications. Native behavior remains
unverified until device tests pass.

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

Local transactional execution supports one SQLite worker. External sends persist
an effect-start marker before network I/O; crash recovery never automatically
repeats a potentially accepted send. Provider verification and complete retention
and account-deletion workflows remain unfinished. A lease or stable Message-ID
is not an exactly-once delivery guarantee.

Application records are workspace-scoped. Production requires PostgreSQL forced
RLS and a non-owner, non-superuser runtime role without BYPASSRLS. Schema/version
and policy checks fail closed at startup; actual PostgreSQL role/isolation tests
must pass before enabling untrusted accounts. SQLite ORM tests are not proof of
database-level isolation. Back up before running versioned migrations.

## Reporting

Do not post tokens or private workspace exports in issues. If this repository is
made public, enable GitHub private vulnerability reporting before accepting
security reports. Contact the repository owner privately for sensitive findings.