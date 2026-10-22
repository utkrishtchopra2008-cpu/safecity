# Final verification status

This repository contains a partial SafeCity implementation. It is not production-ready and does not yet meet the full PRD or endpoint catalogue. Implemented slices include PostgreSQL schema/migrations, session authentication and CSRF, incident/review workflows, technical-admin source registration/upload, bounded video upload validation, private Supabase Storage, a PostgreSQL worker, optional CPU object/face-region observations, public-context Search/Fetch, and frontend review/system screens.

## Verification run

| Area | Result |
|---|---|
| Backend Ruff lint | Passed with the locked backend environment. |
| Backend Ruff format check | Passed; 54 files formatted. |
| Backend mypy | Passed; no issues in 41 source files. |
| Backend pytest | 98 passed, 1 skipped (PostgreSQL integration test requires `SAFECITY_TEST_DATABASE_URL`). One Starlette TestClient deprecation warning remains. |
| Locked installs | `uv sync --locked --group dev` and `uv lock --check` passed with Python 3.12.15. `npm ci` passed from `frontend/package-lock.json`; local Node 24.22.0 emitted the expected engine-range warning because the project specifies Node 22.x. |
| PostgreSQL | A disposable PostgreSQL run earlier in this work session exercised migration downgrade/upgrade, schema checks, duplicate-ingestion conflict, rollback, and append-only audit trigger. This was not a live Supabase project. |
| Frontend lint/typecheck/unit tests/build | Passed; 12 Vitest tests, including the AppShell skip-link/navigation contract and inert rendering of HTML-like TinyFish text. |
| Frontend format check | Passed. |
| OpenAPI route catalogue | Loaded successfully with 25 paths; only a subset of `API.md` endpoints exists. |
| Docker Compose | `docker compose config -q` passed. No full multi-service app/worker deployment was verified. |
| Live Supabase storage/RLS | NOT RUN; credentials/project were unavailable. |
| Video pipeline/model | A generated short AVI passed real OpenCV decode/quality sampling and optional CPU YOLOX/YuNet processing. Artifacts were verified against pinned source revisions and SHA-256 hashes. Detector tests cover blank frames and normalization; upload tests fault-inject decoder-open, invalid metadata, excessive dimensions/duration, and no-frame failures. These object/face-region observations never create incident records. A broader real-codec/corrupt-file and production resource matrix is NOT RUN. No event detector is available. |
| TinyFish | Search/Fetch request handling, URL boundaries and provider failures passed mocked tests; source-level refresh passed SQLite persistence/deduplication and disabled-provider tests. No live request or PostgreSQL queue integration was run; no key is configured. |
| Visual and accessibility review | Partial manual review: login and protected-route error states were inspected in the browser; responsive header checked at 1024 px and 390 px, with no horizontal overflow at 390 px. Full-page screenshot and keyboard/contrast audit remains NOT RUN. |

The latest local regression run also covers rejection of expired/revoked sessions, client filename path traversal, deterministic demo-seed idempotency/production guard, configured per-instance source/evaluation rate limits, inert external-content rendering, and operator job ownership with safe diagnostic/result redaction. `docs/threat-model.md` maps controls, tests, and remaining limits. GitHub Actions backend and frontend checks passed on the previously published commit `30a84a9`; this verification-only test addition still needs its CI run.

## Operational constraints and remaining requirements

- Optional local walkthrough fixture: after applying migrations, from `backend/` run `uv run python -m app.cli.seed_demo --apply` with `APP_ENV=development` and a development-only `DATABASE_URL`. It refuses shared/production modes and adds a plainly labelled synthetic sample with no detector score or reliability claim. See `docs/demo-data.md`.
- Threat model and rate limits: `docs/threat-model.md` records account/session, authorization, CSRF, upload/parser, resource, secrets, storage URL, public-content injection, SSRF, provider-rate, and audit/deletion risks with tests and remaining limits. API defaults for this single-instance MVP are in `API.md` §9.3; shared deployment must enforce limits at the trusted proxy or shared boundary.
- Orphan cleanup is manual by design; see `docs/supabase-storage.md`. The operator must choose an age threshold, inspect the dry-run object list, then explicitly pass `--apply`. No automatic retention threshold is introduced.

- Apply `backend/migrations` to a configured PostgreSQL database before running authenticated workflows. Use backend-only `DATABASE_URL`; configure Supabase URL/service role and private bucket for video uploads.
- `docs/supabase-storage.md` documents the deny-by-default Storage policy path. These policies have not been applied or tested against a live project. Backend resource checks remain required because a service-role key bypasses RLS.
- A single PostgreSQL worker claims jobs, recovers expired leases, retries bounded transient storage failures, and records OpenCV video-quality measurements plus optional object/face-region observations. The generated AVI exercised the real CPU model path. It creates no incidents. Worker liveness is not reported by the API (`worker: not_reported`).
- Evidence metadata/content routes now enforce operator/supervisor roles and the content route issues a 120-second private signed redirect. Live Supabase access and source membership/tenant authorization are unverified; the database schema has no tenant/source membership model.
- Evaluation metric calculations now exist as a bounded, hand-fixture-tested pure service with a documented matching rule. Evaluation list/detail APIs and a results page exist; creation remains blocked with `DETECTOR_UNAVAILABLE` because the installed YOLOX/YuNet models do not implement an event taxonomy. Metric calculation is not connected to evaluation-run persistence. Public-web Search, selected-result Fetch, and source-level asynchronous refresh are implemented behind authenticated backend routes and the database worker; mocked provider and SQLite idempotency tests passed, but live provider/PostgreSQL queue integration was not run. Configure the optional key locally with `cd backend && python -m app.cli.configure_tinyfish`; no key is required for tests or core workflows. The dashboard shows persisted counts and recent records; reliability display reads stored evaluation metrics and reports absent results as unavailable. Worker cancellation remains incomplete. `backend/app/cli/cleanup_orphan_storage.py` offers a bounded, explicit dry-run-first cleanup of old unreferenced generated uploads; it has not been run against live Supabase. Basic source reprocessing, job status, and aggregate system status reads exist; the system screen labels worker liveness as unreported and video processing as quality plus optional object observations.
- Retention remains non-destructive and approval-dependent. No real detector result, reliability score, live CCTV status, or production performance claim is made.

## Changed implementation areas

- Database models/migration, upload validation and Storage adapter: `backend/app/db`, `backend/migrations`, `backend/app/media`, `backend/app/storage`.
- Optional pinned CPU observation models, source/upload admin workflow, deterministic local demo seed, request limits, explicit orphan cleanup, and TinyFish inert-text regression: `backend/app/services/opencv_models.py`, `backend/app/cli/download_models.py`, `backend/app/cli/seed_demo.py`, `backend/app/cli/cleanup_orphan_storage.py`, `backend/app/services/storage_cleanup.py`, `backend/app/core/rate_limit.py`, `frontend/src/components/SourceAdminPanel.tsx`, `frontend/src/pages/PublicContextPage.test.tsx`, `docs/model-artifacts.md`, `docs/demo-data.md`, `docs/supabase-storage.md`, `docs/threat-model.md`.
- Worker integration and safe result metadata: `backend/app/worker.py`, `backend/app/api/v1/jobs.py`.
- Auth, incident/review and source routes/services: `backend/app/api/v1`, `backend/app/services`, `backend/app/main.py`.
- Frontend login and incident workflows: `frontend/src/api`, `frontend/src/app/router.tsx`, `frontend/src/pages`, `frontend/src/styles/global.css`.
- Contract and setup notes: `API.md`, `ARCHITECTURE.md`, `DATABASE.md`, `.env.example`, `docs/implementation-audit.md`, `docs/implementation-decisions.md`, `docs/supabase-storage.md`.
