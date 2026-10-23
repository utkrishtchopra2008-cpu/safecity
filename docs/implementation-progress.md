# Implementation progress

Updated: 2026-10-23

## Prompt 0 — Execution contract and baseline

**Status:** PASS — baseline and documentation gate complete; no feature phase started.

### Completed

- Cloned `https://github.com/utkrishtchopra2008-cpu/safecity` into this workspace and confirmed `main` at `f799344`, tracking `origin/main`.
- Confirmed the initial working tree is clean and reviewed `AGENTS.md`, all six source-of-truth documents, the implementation plan, CI workflow, manifests, lockfiles, README, existing audit, decisions, and recent Git history/diff.
- Refreshed [implementation-audit.md](implementation-audit.md) with current checkout facts, the requirement-to-file/test traceability matrix, and this run's check results. The matrix remains partial for several acceptance criteria.
- Corrected stale current-state claims in `README.md` and added the existing demo URL under `Demo Video`.
- Corrected the stale planning-basis statements in `IMPLEMENTATION_PLAN.md` so it no longer describes this checkout as documentation-only.
- Reviewed `docs/demo-data.md`: the local walkthrough uses synthetic, labelled data. Recorded that the linked demo video has no documented footage provenance/usage permission and is not treated as test, training, or evaluation data.
- Reviewed `docs/implementation-decisions.md`; existing unresolved product choices and architecture decisions remain explicit, and no new product behavior was inferred.

### Verification

- `make check` — **PASS** with Python 3.12.14, Node 22.16.0, `backend/uv.lock`, and `frontend/package-lock.json`.
- Backend: Ruff lint passed; Ruff format check passed (56 files); mypy passed (40 source files); pytest **100 passed, 3 skipped**. Skips: two tests require verified local model artifacts; one requires `SAFECITY_TEST_DATABASE_URL` to identify a disposable migrated PostgreSQL database. One Starlette/httpx deprecation warning remains.
- Frontend: ESLint passed; Prettier check passed; TypeScript check passed; Vitest **16 passed** across 7 files; Vite production build passed.
- `git diff --check` — **PASS**. The only edits are documentation. `.venv`, `node_modules`, downloaded runtimes, and package caches are local verification artifacts, not deliverables.
- GitHub Actions for current `origin/main` was not queried in Prompt 0. No push occurred, so no push/Actions verification is claimed.

### Blockers and known documentation drift

- PostgreSQL integration and configured model-artifact tests remain skipped because their required disposable database and verified local model files are not configured. Live Supabase/TinyFish behavior is not demonstrated by `make check`.
- GitHub Actions status for the current remote HEAD remains NOT RUN/NOT VERIFIED; local checks do not substitute for that result.
- Product decisions requiring approval remain listed in `PRD.md` and `docs/implementation-decisions.md`; no new product assumption was made in this baseline.

### Next

Prompt 1 audit gate is documented below. Exact next phase: **Prompt 2**.

## Prompt 1 — Repository audit and traceability

**Status:** PARTIAL — audit and risk map complete; current remote Actions result is unverified because the available feed has no current-HEAD run and the exact-SHA combined status is empty; PR-only workflow lookup cannot verify push-triggered runs.

### Completed

- Inspected tracked/untracked state, branch/remotes/history/diff, all six source-of-truth Markdown documents, README/current-state docs, backend/frontend trees, routers/models/migration/tests, package manifests/lockfiles, Compose, environment example, Makefile and CI.
- Local tree was clean before this audit. Local `main` is at `76b898dacca311c64776084b69067f79190da623`; its cached `origin/main` remains `f799344`. GitHub's connected integration verified remote `main` at `420197b2cb491108d63053a858ab621beae44371`. Do not refresh refs manually; shell transport is unavailable.
- Verified run #16 (`ae285428e1b4c23e46fd3e1d57619093618bd89a`) failed at backend mypy due to missing `app.media.uploads`; run #17 (`a7c8be49c10f53c7b140fed1128694f3d001f1c2`) passed after adding that module. Run #40 is successful on older SHA `485c84c7b437adf23ff736bb870c5de99859f823`; it is not evidence for current remote HEAD.
- Updated `docs/implementation-audit.md` with exact current Git/Actions state, detailed paths and line anchors, subsystem and requirement-to-file/test traces, ranked gaps, runtime/check commands, and a per-file inventory for all 128 tracked files. All tracked paths are KEEP; generated local ignored artifacts are identified as eventual cleanup candidates but were not removed.
- Updated `docs/implementation-decisions.md` with the verified CI diagnosis and retained cancellation's missing API/database semantics as a contract blocker.
- `IMPLEMENTATION_PLAN.md` already had its stale documentation-only premise corrected during Prompt 0, preserving its original planned-phase intent; audit now distinguishes plan from present evidence.
- No application-code files changed and no files were deleted.

### Verification and evidence

- Read-only inspection commands: Git status/log/remotes/diff/index, tracked file inventory, ignored status and suspicious-file search, source/route/test/reference searches; no repository mutation before the audit/risk map was complete.
- Runtime discovery: host Node `v24.22.0`, Python `3.14.7`, Docker `29.8.2`, Docker Compose `v5.6.0`; `uv` is not on current shell PATH. Project runtime constraints are Python 3.12 and Node 22. Prompt 0's prior `make check` used Python 3.12.14/Node 22.16.0 and passed: backend 100 passed/3 skipped, frontend 16 passed, lint/format/type checks/build passed. Prompt 1 did not rerun tests or start Compose.
- GitHub: latest Actions page entry #40 succeeded on older SHA; exact current SHA query returned empty combined status; the connector workflow lookup is PR-only and Actions feed has no current-HEAD run. Current Actions is NOT VERIFIED, not PASS.
- `git diff --check` — **PASS** after the documentation update. Final review confirmed only the three requested audit documents changed. No tests were rerun for Prompt 1 because no application code changed; the latest actual test results remain the Prompt 0 `make check` results above.

### Blockers and ranked next work

- **P0:** Verify complete role/resource ownership for evidence and source records; apply/test live private bucket/RLS policy; do not assert tenant-level isolation unsupported by the schema.
- **P1:** Keep incident/event inference and persisted evaluation BLOCKED until an approved event model and labeled dataset exist; expand endpoint positive/negative/error tests; define cancellation API/database transition semantics before implementing a cancel route; complete UI states and accessibility review.
- **P2:** Verify current-commit Actions, live TinyFish if deliberately configured, worker liveness/monitoring, performance bounds, retention approval, backup/restore and deployment rollback.
- Job cancellation remains contract-blocked as recorded in `docs/implementation-decisions.md`; do not infer a cancellation route or state transition.

### Next

Prompt 1 audit gate is complete. Exact next phase: **Prompt 2**.

## Prompt 2 — Database, migrations, sessions, and private storage

**Status:** PASS for implementation and locally runnable verification; live Supabase checks remain BLOCKED/NOT RUN because no project credentials are configured. Existing models/migration and storage lifecycle match the inspected contracts; a signed-key validation gap is fixed and mock-tested. Fresh PostgreSQL migration, integrity, and downgrade/upgrade round-trip checks pass against an isolated disposable container.

### Completed

- Re-inspected `DATABASE.md`, `API.md`, `ARCHITECTURE.md`, `PRD.md`, SQLAlchemy models, the initial Alembic revision, upload/evidence/session routes, private-storage adapter, cleanup CLI, environment configuration, Compose, and relevant tests before edits.
- Confirmed the 16 schema entities in `backend/app/db/models.py` and `backend/migrations/versions/0001_initial_schema.py` cover the specified users, hashed sessions, jobs, sources, incidents, evidence/associations, assessments, reviews, evaluation data/runs/metrics, audit events, and attributed external context. The migration uses explicit DDL, includes FK/check/unique/index constraints and append-only audit trigger, has reverse-order downgrade SQL, and does not use `Base.metadata.create_all()`.
- Compared SQLAlchemy metadata with the initial revision: all 16 modeled tables are present in the migration, with no migration-only tables.
- Fixed `SupabaseStorage.signed_url()` to reject absolute/traversal/backslash keys before network access, using the same validation rule as other object operations. Added a negative mock test in `backend/tests/test_supabase_storage.py`.
- Updated `docs/supabase-storage.md` with the actual local migration and mock-test setup, corrected the obsolete claim that upload/evidence routes are not implemented, and clearly marked live private-bucket verification as unverified.
- No schema migration was added because model/revision review found no demonstrated contract mismatch. No data, evidence, or files were deleted.
- Started a temporary PostgreSQL 16 container with no persistent volume on a test-only port, applied the clean migration, ran the PostgreSQL integrity test successfully, downgraded to base, upgraded again, reran the integrity test successfully, then removed the container. No persistent database or test data remains.

### Verification

- Backend Ruff lint — **PASS**; Ruff formatting check — **PASS** (56 files); mypy — **PASS** (40 files).
- Backend pytest — **101 passed, 3 skipped**. Skips: two checks require verified model artifacts; PostgreSQL integrity test requires `SAFECITY_TEST_DATABASE_URL` pointing to a disposable migrated DB. Storage mock tests, including signed-key traversal rejection, passed. One existing Starlette/httpx deprecation warning remains.
- Frontend ESLint — **PASS**; Prettier check — **PASS**; TypeScript — **PASS**; Vitest — **16 passed**; Vite production build — **PASS**.
- Alembic generated offline PostgreSQL SQL for both `upgrade head` and `downgrade 0001_initial_schema:base` — **PASS**. This validates migration generation and downgrade SQL, not execution against PostgreSQL.
- PostgreSQL integration — **PASS** twice against the disposable database: clean-upgrade integrity run and post-downgrade/upgrade integrity run. This covered invalid interval constraints, concurrent duplicate source-event ingestion, transaction rollback, and append-only audit mutation/deletion rejection. Container removed after use.
- `git diff --check` — **PASS**. Initial backend check attempts from the repository root failed due to configured relative paths; rerunning from `backend/` passed.
- Live Supabase Storage bucket privacy, RLS policies, service-role access, signed URL use, and orphan cleanup — **NOT RUN** (no live project credentials); HTTP-mock coverage passes.

### Remaining blockers and next

- **P0 external verification:** test private bucket/RLS and authorized upload/evidence access on a dedicated non-production Supabase project. Do not treat mocks or service-role adapter tests as proof of live policy.
- **P1:** maintain model/revision parity when schema changes; expand route-level ownership and storage crash-window tests as part of the relevant phases.

Prompt 2 local completion gate is met. Exact next phase: **Prompt 3**. Live Supabase policy/access verification remains an explicitly recorded external BLOCKED/NOT RUN item, as required when credentials are unavailable.

## Prompt 3 — OpenCV video pipeline and verified detection

**Status:** PARTIAL — bounded OpenCV quality sampling and typed detector output contracts are implemented and tested. Pinned detector weights are not present locally, so artifact-backed model execution remains NOT RUN and the runtime must report `MODEL_UNAVAILABLE`. No event detector or incident inference is implemented.

### Completed

- Added typed bounded object boxes/scores and quality measurements in `backend/app/services/video_types.py`. The object API result includes normalized bounds, frame index, decoder timestamp with explicit known/unknown state, detector version, score semantics, and evidence ID; the job API validates nested schemas and caps output at 500 detections and 32 quality measurements.
- Added uniform bounded source-frame selection in `backend/app/services/video_sampling.py`; quality sampling is capped at 181 frames and model sampling at 31. Timestamps come only from decoder `CAP_PROP_POS_MSEC`, must be finite/nonnegative/strictly increasing, and otherwise serialize as unavailable/unknown. FPS is never used to synthesize source timestamps.
- Updated worker quality results with resolution, mean grayscale brightness, documented Laplacian variance, decoded/sample-failure counts, nominal FPS, and timestamp availability. Every metric carries algorithm/version/configuration/status/reason; optional brightness/sharpness thresholds default unset and cause `uncertain` only when explicitly configured and breached. Quality does not create an incident.
- Added streamed upload failure codes for empty, oversized, unsupported codec/container, invalid signature/metadata, and corrupt/truncated no-frame videos. Existing checks enforce the hard byte cap during writes, signature/MIME/extension, stream properties, dimensions, duration, and an initial decoded frame. Partial decode failures later in the clip are recorded as quality uncertainty; full-container decode at intake is not guaranteed.
- Added bounded old-worker-temp cleanup at worker startup; normal processing still unlinks its temp file and closes storage in `finally`. No durable cancellation endpoint/state was invented because API/database contracts do not specify one; a cancellation test exercises resource cleanup.
- Resolved the Prompt 3/API conflict in `docs/implementation-decisions.md`: follow Prompt 3’s bounded object box requirement and update `API.md`; retain face-region counts only and preserve event/incident separation. Updated pinned artifact contract in `docs/model-artifacts.md`.
- Updated `frontend/src/components/SourceAdminPanel.tsx` to show an accessible uncertain-quality warning and reason codes, or explain that thresholds are not configured; `frontend/src/components/SourceAdminPanel.test.tsx` covers the warning state.
- No verified model artifacts were found in `.data/models`; missing files now produce `MODEL_UNAVAILABLE`, while changed bytes produce `MODEL_CHECKSUM_INVALID`. Two real-artifact tests are skipped honestly. There are no fake predictions, event detections, or accuracy claims.

### Verification

- Backend Ruff lint — **PASS**; Ruff format check — **PASS** (59 files); mypy — **PASS** (42 source files).
- Backend pytest — **112 passed, 3 skipped**. Two skips require local checksum-verified YOLOX/YuNet artifacts; one requires a disposable migrated PostgreSQL URL. Targeted pipeline/API tests — **53 passed, 2 skipped**. The full backend suite was rerun after the final timestamp and missing-model-state adjustments.
- Frontend ESLint — **PASS**; Prettier — **PASS**; TypeScript — **PASS**; Vitest — **16 passed** across 7 files; Vite build — **PASS**.
- The `make check` wrapper was not run because `uv` is absent from shell PATH. Every backend and frontend command listed by that target was invoked directly with the repository’s pinned backend virtualenv/frontend install. `git diff --check` — **PASS**.
- Live Supabase and model-weight-backed inference — **NOT RUN**. Test outputs cannot establish live storage privacy or model runtime behavior.

### Remaining blockers and next

- **P1 / unavailable model:** fetch/install the already pinned and hash-verified artifacts in a network-enabled environment, then run both artifact-backed CPU inference tests. Missing artifacts currently fail safely as `MODEL_UNAVAILABLE`.
- **P1 / decoder completeness:** initial-frame validation plus bounded sample decoding does not prove every frame in every container decodes; an adversarial full codec/corruption matrix and hard process-level CPU timeout remain unverified.
- **P0 external:** live Supabase private bucket/RLS and authorized access checks remain blocked on dedicated project credentials.
- Event detection remains unimplemented; do not present object output as event evidence. Durable cancellation remains undefined by contract.

Exact next phase: **Prompt 4**.

## Prompt 4 — Authentication, authorization, and security hardening

**Status:** PARTIAL — session, CSRF, route authorization, and security-header controls are implemented and API-tested; deployment-boundary and comprehensive ownership controls remain explicitly incomplete.

### Completed

- Reconfirmed the API.md cookie-session model as the only auth system; no JWT or second identity provider was introduced.
- Extended API tests for cryptographic session-token hash persistence, idle expiry and inactive-account rejection, untrusted login Origin rejection, protected evidence access by technical administrators, API no-store/security headers, Secure cookies, and conditional HSTS.
- Applied `Cache-Control: no-store` to all API paths and added a restrictive Permissions-Policy; HSTS is emitted in secure-cookie mode.
- Updated `API.md`, `docs/threat-model.md`, `docs/implementation-decisions.md`, and the Prompt 4 traceability delta in `docs/implementation-audit.md`.

### Verification

- Backend Ruff lint — **PASS**; Ruff format check — **PASS** (59 files); mypy — **PASS** (42 source files); full pytest — **118 passed, 3 skipped**, one Starlette/httpx deprecation warning.
- Frontend ESLint, Prettier check, TypeScript, Vitest (**16 passed**) and Vite production build — **PASS**.
- `make check` was attempted but could not start because `uv` is not on PATH; equivalent backend checks ran from the installed project `.venv`, and frontend package scripts ran directly. No push occurred.

### Remaining blockers and next

- **PARTIAL:** no API Host allowlist or global streamed request-body cap; configure Host validation and body-size limits at the trusted ingress. Starlette may spool multipart content before application staging enforces upload caps.
- **PARTIAL:** source/tenant ownership rules are not present in the single-institution schema; current route roles and available job/evaluation ownership checks are tested only in selected paths.
- **NOT RUN/BLOCKED:** cross-replica rate limiting, live Supabase RLS/storage checks, automated repository secret scanning, and external penetration/security review.
- No MFA, recovery, cancellation, deletion, or retention behavior was invented. Retention remains non-destructive/configurable.

Prompt 4 implementation and local targeted verification are complete at the available boundary. Exact next phase: **Prompt 5**.
