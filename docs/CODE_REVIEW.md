# Engineering review — 2026-09-29

## Outcome of this hardening pass

The project had a clear product idea and a functional vertical slice, but the browser received every correct-answer flag and submitted its own score. Anyone could forge public statistics. Quiz IDs used one-second timestamps, repeated submissions created duplicate attempts, deleting a quiz cascaded into permanent attempt loss, import size was unbounded, logs were absent, and the committed SQLite file mixed application code with user data.

This pass moved grading to the server, removed answer keys from the public payload, bounded and canonicalized imports, added UUID-based idempotency, database constraints, collision-resistant quiz IDs, soft deletion, structured logs, request IDs, optional Sentry reporting, health checks, verified SQLite backups, persistent deployment paths, tests, coverage, linting, dependency auditing, and CI.

The historical database remains present in old Git commits. Removing it from the current tree prevents future exposure, but history cleanup requires a coordinated `git filter-repo` rewrite, forced push, collaborator notification, and secret/session review. That destructive operation was intentionally not automated.

## Remaining priorities

### P0 — before inviting outside contributors

1. Choose and add a license. MIT maximizes reuse, Apache-2.0 adds an explicit patent grant, and GPLv3 requires derivatives to remain open.
2. Clean the existing duplicate case-insensitive email group, then move to a custom email-first user model or enforce a safe database uniqueness migration.
3. Copy backups off the Raspberry Pi and perform a documented restore drill. Same-device backups do not protect against disk loss.
4. Enable GitHub private vulnerability reporting, branch protection, required CI, and secret scanning.

### P1 — product readiness

1. Add password reset, email verification, account deletion/export, and a privacy notice.
2. Add quiz visibility states (`private`, `unlisted`, `public`) and unguessable share tokens.
3. Add abuse controls: rate limits, bot protection, moderation/reporting, and storage quotas.
4. Move UI text to Django gettext catalogs and add accessibility plus browser end-to-end tests.
5. Add explicit quiz export/import versioning so schema evolution remains backward compatible.

### P2 — scale and maintainability

1. Add pagination and search to quiz lists.
2. Move production to PostgreSQL when concurrency or multiple app processes outgrow SQLite.
3. Split the large inline editor script into tested JavaScript modules.
4. Publish versioned releases, changelogs, container images, and a supported upgrade policy.
