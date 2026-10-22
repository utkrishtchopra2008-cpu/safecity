# Final verification status

This repository contains a partial SafeCity implementation. It is not production-ready and does not yet meet the full PRD or endpoint catalogue. Implemented slices include PostgreSQL schema/migrations, session authentication and CSRF, basic incident list/detail/review, simulated-source registration, bounded video upload validation, a private Supabase Storage adapter, job/system/reliability read APIs, and frontend login/incident/reliability/system screens.

## Verification run

| Area | Result |
|---|---|
| Backend Ruff lint | Passed. |
| Backend Ruff format check | Passed. |
| Backend mypy | Passed (23 source files). |
| Backend pytest | 65 passed, 1 skipped (optional PostgreSQL integration test; no `SAFECITY_TEST_DATABASE_URL` was set for the latest run). Starlette emitted one TestClient deprecation warning. |
| PostgreSQL | A disposable PostgreSQL run earlier in this work session exercised migration downgrade/upgrade, schema checks, duplicate-ingestion conflict, rollback, and append-only audit trigger. This was not a live Supabase project. |
| Frontend lint/typecheck/unit tests/build | Passed; Vitest 6 tests. |
| Frontend format check | Passed. |
| OpenAPI route catalogue | Loaded successfully with 25 paths; only a subset of `API.md` endpoints exists. |
| Docker Compose | `docker compose config -q` passed. No full multi-service app/worker deployment was verified. |
| Live Supabase storage/RLS | NOT RUN; credentials/project were unavailable. |
| Video pipeline/model | A generated short AVI passed real OpenCV upload/decode and quality-sampling checks. Broader codec/corruption/resource tests and detector execution are NOT RUN; no approved detector artifact/license is present. No detection is fabricated. |
| TinyFish | Search/Fetch request handling, URL boundaries and provider failures passed mocked tests; source-level refresh passed SQLite persistence/deduplication and disabled-provider tests. No live request or PostgreSQL queue integration was run; no key is configured. |
| Visual and accessibility review | NOT RUN as a full page/viewport screenshot audit. |

## Operational constraints and remaining requirements

- Apply `backend/migrations` to a configured PostgreSQL database before running authenticated workflows. Use backend-only `DATABASE_URL`; configure Supabase URL/service role and private bucket for video uploads.
- `docs/supabase-storage.md` documents the deny-by-default Storage policy path. These policies have not been applied or tested against a live project. Backend resource checks remain required because a service-role key bypasses RLS.
- A single PostgreSQL worker claims jobs, recovers expired leases, retries bounded transient storage failures, and records OpenCV video-quality measurements. Its quality-only sampling path passed a generated AVI fixture. It creates no incidents and runs no object detector. Worker liveness is not reported by the API (`worker: not_reported`).
- Evidence metadata/content routes now enforce operator/supervisor roles and the content route issues a 120-second private signed redirect. Live Supabase access and source membership/tenant authorization are unverified; the database schema has no tenant/source membership model.
- Evaluation metric calculations now exist as a bounded, hand-fixture-tested pure service with a documented matching rule. Evaluation list/detail APIs and a results page exist; creation is intentionally blocked with `DETECTOR_UNAVAILABLE` because no verified detector handler/model artifact is installed. Metric calculation is not connected to evaluation-run persistence. Public-web Search, selected-result Fetch, and source-level asynchronous refresh are implemented behind authenticated backend routes and the database worker; mocked provider and SQLite idempotency tests passed, but live provider/PostgreSQL queue integration was not run. Configure the optional key locally with `cd backend && python -m app.cli.configure_tinyfish`; no key is required for tests or core workflows. The dashboard shows persisted counts and recent records; reliability display reads stored evaluation metrics and reports absent results as unavailable. Worker cancellation/orphan cleanup and deletion remain incomplete. Basic source reprocessing, job status, and aggregate system status reads exist; the system screen labels worker liveness as unreported and video processing as quality-only.
- Retention remains non-destructive and approval-dependent. No real detector result, reliability score, live CCTV status, or production performance claim is made.

## Changed implementation areas

- Database models/migration, upload validation and Storage adapter: `backend/app/db`, `backend/migrations`, `backend/app/media`, `backend/app/storage`.
- Auth, incident/review and source routes/services: `backend/app/api/v1`, `backend/app/services`, `backend/app/main.py`.
- Frontend login and incident workflows: `frontend/src/api`, `frontend/src/app/router.tsx`, `frontend/src/pages`, `frontend/src/styles/global.css`.
- Contract and setup notes: `API.md`, `ARCHITECTURE.md`, `DATABASE.md`, `.env.example`, `docs/implementation-audit.md`, `docs/implementation-decisions.md`, `docs/supabase-storage.md`.
