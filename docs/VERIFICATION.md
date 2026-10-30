# v0.1 verification

Local verification on Linux, 2026-10-30. These results describe the current
development version, not a production or app-store certification.

## Passed

- Backend: 20 pytest tests covering task and memory persistence, exact-content
  approvals, stale edits, cancellation, retry, lease recovery, calendar imports,
  planning, access control, external model consent, export and data deletion.
- Python: Ruff lint and formatting checks.
- Web: TypeScript check, Vite production build and Oxlint.
- Dependency installation: npm audit reported zero known vulnerabilities at the
  time of installation. This is not a security audit.
- Compose: configuration validation with non-secret placeholder credentials.
- Capacitor: Android and iOS project generation and synchronization.
- Integrated browser, isolated demo database: proposals produce no task before
  approval; a revised and approved proposal is executed once by the worker with
  the revised content. Memory creation, editing and deletion persist.
- Integrated browser: task creation, editing and completion; navigation across
  all six views at actual CSS viewports of 1440 x 900 and 390 x 844; no horizontal
  overflow. Mobile navigation and task dialog fit; the original bitmap loads.
  Desktop and mobile screenshots were inspected.

## Not Verified

- The standalone Playwright suite was discovered but not executed: this host's
  corporate proxy policy blocks the Chromium download. Integrated browser
  checks above are separate checks, not a passing Playwright suite result.
- Docker image build, Compose deployment and PostgreSQL runtime behavior.
- Live model responses, provider availability or model quality. All execution
  tests use the explicit offline demo provider or controlled test doubles.
- Native compilation, signing, device behavior, notifications or store review.
- Multi-worker SQLite execution, external side-effect exactly-once behavior,
  multi-user isolation or public-internet production readiness.

CI includes the standalone browser suite for an environment where the browser
can be installed. A remote CI result is not implied by these local checks.