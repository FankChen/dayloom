# Verification

Unreleased implementation verified locally on Linux, 2026-11-02. These results
are development evidence, not production, native-device or store certification.
See [OPERATIONS.md](OPERATIONS.md) for deployment prerequisites and limitations.

## Passed Local Checks

- Backend: **41 passed, 1 skipped** using `uv run pytest backend/tests -q`.
  The skip is the real PostgreSQL integration test, not a successful isolation run.
- Original task/memory/planning/calendar behavior, exact-content approvals,
  optimistic edits, local worker recovery, export and deletion regression tests.
- Workspace-scoped reads, aliases, writes and workers; cross-workspace mutation
  rejection; versioned SQLite migration retaining legacy records.
- Signed OIDC Authorization Code/PKCE exchange with mocked HTTP transport,
  signature/issuer/audience/nonce validation, native PKCE-bound single-use ticket,
  cookie CSRF protection, session rotation and revocation. Real OAuth classes are
  used; the identity provider itself is not a live service in these tests.
- Encrypted workspace model credentials, secret-free API reads, approved endpoint
  checks, explicit external-context consent, request quotas and no implicit demo fallback.
- SMTP with a controlled test double: approval, connection revocation, ambiguous
  effect recovery without replay, fixed-content finite schedules, source-proposal
  consumption, pause and owner-reported outcome handling.
- Browser runner authentication and approved-origin/redirect boundaries with test
  doubles. These tests do not establish real Chromium or network isolation.
- `npm run check`: Ruff lint/format, Oxlint, TypeScript and Vite production build.
  The changed frontend sources were formatted and the frontend gates rerun.
- `npx cap sync` in `apps/web`: final web assets and App/Browser plugins synchronized
  into both native projects. This is not a native compilation result.
- Compose/workflow/identity-realm and native manifest/plist structural checks.
  Both native CI jobs' actual URL guard code was exercised with accepted HTTPS
  and rejected HTTP, userinfo, query-string and fragment inputs.

## Integrated Browser Acceptance

The upgraded preview used `data/preview-v02.db`, created with SQLite's backup API
from the existing local database. All five original tasks remained after migration.
The original database and previous development service were left untouched.

- Model configuration saved with a synthetic key, checked for secret-free reads
  and disconnected. No connection-test button or live provider call was used.
- Synthetic SMTP connection saved without credential disclosure. A mail proposal
  remained pending with zero execution attempts before authorization.
- An exact-content schedule was reviewed, authorized for the following day with
  a one-run limit, and paused. API verification confirmed zero generated runs,
  the consumed source proposal cancelled with zero attempts, and no active test
  schedule. The synthetic mailbox was disconnected afterward.
- Actual CSS viewports of 1440 x 900 and 390 x 844: Settings and Activity layout
  checks found no horizontal overflow. The mobile model dialog and its controls
  fit within the viewport. Available desktop/mobile screenshots were inspected.
- Some final controls were activated through DOM events because the integrated
  browser was background-hidden and pointer clicks timed out. State assertions
  used the actual UI handlers and live preview API. Screenshots from a hidden view
  can be stale or clipped; these checks are not a full pointer-interaction suite.

No real email, purchase, paid service provisioning or public publication occurred.
The previously recorded v0.1 browser checks on 2026-10-30 covered the original
six views, task/memory CRUD and local proposal approval/execution; they are not
new evidence for native or account-mode behavior.

## Not Verified or Not Implemented

- Standalone Playwright execution: this host's corporate policy blocks Chromium
  downloads. The integrated browser checks are separate, not a CLI suite pass.
- Docker image/Compose deployment, real PostgreSQL RLS/runtime-role behavior and
  Keycloak deployment. Docker socket access was denied; no privilege escalation
  was attempted. CI contains a dedicated PostgreSQL service/role test gate.
- Live model, SMTP and isolated-browser execution. No real credentials were used.
  Provider compatibility, delivery and network/DNS isolation remain deployment gates.
- Android/iOS compilation, signing, installable artifacts, actual secure storage,
  native callback handling, notification capture and real-device accessibility.
  Android SDK/Java were unavailable locally; iOS compilation needs macOS/Xcode.
- The manual native workflow was not dispatched. No remote CI success, signed
  APK/AAB, TestFlight build or store readiness is claimed.
- Purchasing, Gmail/Graph OAuth, dynamic-content automation, full account deletion,
  identity-provider backchannel logout, KMS, Temporal/LangGraph, monetary billing
  limits, push, share extensions and offline synchronization remain unfinished.
- Multi-worker SQLite, external exactly-once effects and public production readiness
  are not claimed. A PostgreSQL policy definition is not proof of effective isolation.

## Environment Notes

Tests emit upstream Authlib/Starlette warnings about their future HTTPX migration.
The multi-project editor's Python environment reports unresolved SQLAlchemy imports
in some files; the project-local `uv` environment resolves them and passes tests.
No workspace-wide interpreter change was made to affect unrelated projects.

CI includes browser, PostgreSQL and manual native workflows for appropriately
provisioned environments. Local checks do not imply those remote jobs have run.