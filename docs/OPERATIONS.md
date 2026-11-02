# Unreleased Account and Native Build Operations

This document describes the current implementation, not all features in the
target architecture. Do not start a public service using the local development
profile or claim that a generated native project is a signed release.

## Local profile

The existing launcher still supports a local, single-workspace profile. Before
starting the changed backend against an existing database, stop its old API and
worker and back up SQLite using the SQLite backup API. Startup runs Alembic
migrations. Existing records stay in the legacy local workspace; new accounts
receive different workspaces and do not inherit that data.

Local model/mail credentials use an encryption key in the ignored
`data/credentials.key` with owner-only permissions unless
`DAYLOOM_CREDENTIAL_KEY` is configured. Back up the key separately and securely:
losing it makes encrypted credentials unusable. Never commit it.

## Account development profile

The included Keycloak profile is for loopback development only. It needs a Docker
daemon the developer is already authorized to use. It does not configure a public
production identity provider, SMTP password recovery or verified-email delivery.

1. Set `DAYLOOM_IDENTITY_ADMIN_PASSWORD` locally and start
   `docker compose -f compose.identity.yaml up -d`.
2. Create a 32-byte Fernet key locally and set `DAYLOOM_CREDENTIAL_KEY`. Generate
   it in your own terminal with `uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`;
   do not send the output in chat or store it in version control.
3. Configure `DAYLOOM_AUTH_BACKEND=OidcAccess`,
   `DAYLOOM_OIDC_ISSUER=http://127.0.0.1:8089/realms/dayloom`,
   `DAYLOOM_OIDC_CLIENT_ID=dayloom`, `DAYLOOM_OIDC_ALLOW_HTTP=true`, and
   `DAYLOOM_PUBLIC_URL=http://127.0.0.1:5178` in the ignored local environment.
4. Run `npm run dev`. The sign-in button opens the identity provider. Register
   test accounts there. Never use real production passwords in this local realm.
5. In Settings, save a model endpoint/model/key, then explicitly test it. The
   test makes a real provider request and counts toward the daily request limit.
   Account mode has no automatic demo fallback.

For native login, use a reachable HTTPS API and HTTPS identity provider, matching
redirect registration, and the same public API URL in the compiled client. A
phone cannot use the development machine's loopback address. The native custom
scheme is protected by a separate PKCE verifier; a one-time ticket, not a bearer
credential, is returned through that URL. Verified universal/app links remain a
release-hardening follow-up.

## Model and mail connections

Only administrator-approved HTTPS model origins and SMTP hosts are selectable.
Do not add untrusted or private-network hosts to the allowlists. The default
model adapter uses Chat Completions with JSON object output; incompatible APIs
fail visibly. Limits are daily request counts and maximum output tokens, not a
currency-denominated billing guarantee or provider invoice reconciliation.

SMTP credentials are encrypted and never returned through configuration/export
APIs. Use an account-specific app password where the provider supports it.
Provider policy may disable password-based SMTP entirely; the current SMTP
connector does not replace Gmail/Microsoft OAuth integrations, which remain
unfinished. Creating a mail connection does not send anything. Preparing a mail
creates an approval-bound action. SMTP acceptance is not delivery confirmation.

Scheduled mail uses exact frozen content, finite runs and an expiry. It is not a
model-generated recurring summary. Preview and explicitly authorize the schedule;
the original one-off proposal is consumed so it cannot also be approved separately.
Pause cancels queued executions and blocks later commits where still possible.
An external operation already accepted by a provider cannot be recalled by pause.
Uncertain effects are not retried automatically. Owner-reported resolution is
labeled as such and is not independent delivery verification.

The scheduler is database-backed in this implementation. Temporal/LangGraph,
dynamic content mandates, generalized compensation and a full effect ledger are
still target-architecture work, not dependencies silently claimed as implemented.

## Production account profile

`DAYLOOM_PRODUCTION=true` requires OIDC, PostgreSQL, HTTPS public/issuer URLs and
an externally supplied encryption key. Use separate database owner/migration and
application roles. Never configure the application role as superuser, BYPASSRLS,
or table owner. Apply migrations with the owner before deployment using
`PYTHONPATH=backend uv run python -m dayloom.bootstrap`, then grant only required
schema usage and table CRUD to the application role. The API/worker refuse to
start if the schema version or workspace RLS checks are wrong.

Migration and application database URLs must be different local secrets. Runtime
initialization does not migrate production schemas using the application role.
PostgreSQL RLS is installed for user-owned tables and transaction-local workspace
context is set on scoped sessions. The live PostgreSQL integration test must pass
in the deployment environment before exposing multiple accounts. CI adds a real
PostgreSQL role/isolation gate; a SQLite test does not prove that gate.

Configure the identity provider with exact redirect URLs, verified email and
recovery delivery, passkeys/MFA as appropriate, restricted registration, external
identity linking policy, and a production backing database. Session revocation
inside Dayloom is immediate; global identity-provider logout/backchannel revocation
is not implemented. Full account deletion and privacy lifecycle are release gates.

The current credential store uses an application encryption key, not KMS envelope
encryption. Provide that key through a secret manager and protect/rotate it with a
reviewed migration procedure. KMS integration, at-rest user-content encryption,
security review, retention jobs, monitoring and restore drills are still required
before describing this implementation as production-ready.

The existing `compose.yaml` remains a local single-workspace deployment. It now
requires one shared `DAYLOOM_CREDENTIAL_KEY` so API and worker can decrypt the same
credentials; it is not the production multi-account deployment manifest.

## Browser worker

The implemented capability is approved public-page reading, not arbitrary
clicking, account login or checkout. Install the optional `browser` Python extra
and provision Chromium only in an environment that permits it. Do not bypass
corporate browser-download policy.

Run `dayloom.browser_server:create_app --factory` under Uvicorn in a separate,
non-root, sandbox-enabled environment. Configure matching
`DAYLOOM_BROWSER_SHARED_TOKEN` values (at least 32 characters), explicit
`DAYLOOM_BROWSER_ALLOWED_ORIGINS`, and `DAYLOOM_BROWSER_EGRESS_PROXY` on the worker.
Set `DAYLOOM_BROWSER_RUNNER_URL` on the API/work worker. Do not expose the runner
publicly. No runner configuration means the capability remains disabled.

The egress proxy and network policy must block direct outbound connections,
private/loopback/link-local/metadata IPv4 and IPv6 destinations, DNS rebinding and
unapproved redirects/subresources. Merely specifying a proxy URL does not prove
network isolation. The browser has JavaScript, service workers, uploads and form
submission disabled and uses a fresh browser per operation. Some modern sites
will therefore not render completely; this is intentional, visible scope.

## Android and iOS artifacts

The `Native packages` workflow is manual. Provide a deployed HTTPS API URL.
Without release signing enabled it creates a clearly labeled internal debug APK
and compiles an unsigned iOS simulator app. These are not store releases.

For a signed Android APK/AAB, the owner configures repository secrets
`DAYLOOM_ANDROID_KEYSTORE_BASE64`, `DAYLOOM_ANDROID_STORE_PASSWORD`,
`DAYLOOM_ANDROID_KEY_ALIAS`, and `DAYLOOM_ANDROID_KEY_PASSWORD`, then explicitly
selects signed Android mode. Keep the signing identity and backups under owner
control. The workflow uploads private CI artifacts and does not publish releases
or change repository visibility. Artifacts expire after seven days.

iOS TestFlight/App Store release still requires an Apple developer team,
provisioning/signing and a device-tested archive. The simulator artifact cannot be
installed on an ordinary iPhone. The native bridge code must compile and pass real
device tests before its secure-storage or notification behavior is certified.

Android notification capture is local-only, disabled by default, based on user
selected sources currently visible to the notification listener. Capture is
encrypted, capped at 100 events, retained at most 24 hours and filtered for common
authentication-code content. Pattern filtering cannot guarantee detection of all
sensitive content; keep sensitive apps unselected. Permission loss clears capture
and disables it. Uploading one captured item as a task is an explicit user action.
iOS cross-app notification reading is not available. Push delivery, native share
extensions, offline task synchronization and full UI localization remain follow-ups.

## Unimplemented commerce

No live purchase integration is enabled or claimed. Selecting an authorized
merchant API, customer/payment grants, sandbox credentials, exact quotation and
budget rules is necessary before implementing checkout. The browser reader
cannot submit orders. A generic payment SDK is not authorization to buy from
arbitrary merchants, and real purchases need separate explicit approval.