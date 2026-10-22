# SafeCity AI — Implementation Plan

**Status:** Proposed development sequence  
**Scope:** MVP described in `PRD.md`, including TinyFish-powered public context enrichment  
**Rule:** This document is a plan only. It does not assert that any application code, endpoint, database migration, or integration is already implemented.

## Planning Basis

This plan follows `PRD.md`, `DESIGN.md`, `ARCHITECTURE.md`, `DATABASE.md`, `API.md`, and `AGENTS.md`. The repository currently contains these specifications and no application scaffold, so Phase 1 establishes the project structure before feature work begins.

### Fixed implementation boundaries

- Frontend: React, TypeScript, Vite, React Router, TanStack Query, and the documented CSS token/component approach.
- Backend: Python 3.12, FastAPI, Pydantic, SQLAlchemy 2, Alembic, and PostgreSQL.
- Processing: one database-backed job queue and one worker for the MVP; use the existing HTTP client (HTTPX) for external calls.
- Media: private local storage for development, behind a storage adapter so a later approved storage implementation does not leak into business logic.
- Detection: one detector adapter, or a clearly labelled simulated detector until an actual model is selected and validated.
- TinyFish: server-side Search and Fetch for optional-per-source public contextual enrichment. No CCTV video, extracted frames, personal data, credentials, or non-public information may be sent to the provider.
- Product safety: no facial recognition, identity tracking, individual criminality scoring, automated accusations, or autonomous dispatch/punitive actions. Public context cannot prove an incident or alter detector/review outcomes.

### Decisions to confirm at the point they become blockers

Record decisions in the relevant source-of-truth spec rather than silently assuming them: initial detector/model and event categories; permissible video/test data and dataset license; video retention; quality/abstention thresholds; hosting and production storage; authentication mode for the demo; initial public-context area granularity, topic allowlist, domain policy, excerpt retention, and freshness windows. Use safe documented defaults for reversible low-risk choices.

---

## Phase 0 — Repository Baseline and Delivery Decisions

### Goal
Establish a verified baseline and turn the specifications into a task checklist before application changes begin.

### Features and tasks
1. Inspect the repository tree, Git state, commit history, and any existing hidden configuration or tests.
2. Reconfirm that the actual codebase is documentation-only; do not assume planned folders or files already exist.
3. Map each P0 PRD requirement to the planned phase and acceptance test.
4. Create a list of decisions that block implementation versus those that can use documented defaults.
5. Confirm permitted demo video/data, retention expectations, public-context source policy, and local run requirements before enabling real data or external calls.

### Files or modules likely affected
- `IMPLEMENTATION_PLAN.md` (this plan, if sequencing decisions materially change).
- The applicable decision/assumption sections of `PRD.md`, `ARCHITECTURE.md`, and `API.md`, only where approval or clarification is needed.
- No application modules yet.

### Dependencies / prerequisites
- Read all six project documents.
- Access to the repository and any approved sample data/model requirements.

### Database / API changes
- None. This phase verifies the design; it does not create a schema or endpoint.

### Tests required
- No application tests yet.
- Check repository state and confirm the planned files do not overwrite existing user work.
- Build a traceability checklist connecting P0 requirements to later tests.

### Completion criteria
- Baseline and missing files are documented.
- Blocking decisions are listed explicitly.
- No product or safety boundary has been silently broadened.
- The first code change has a clear, testable scope.

---

## Phase 1 — Project Scaffold, Tooling, and Configuration

### Goal
Create a reproducible frontend/backend project skeleton and establish basic development checks.

### Features and tasks
1. Add the frontend scaffold with Vite, React, TypeScript, the established routing/server-state libraries, and the existing CSS strategy.
2. Add the backend scaffold using Python 3.12, FastAPI, Pydantic, SQLAlchemy 2, Alembic, and the existing HTTPX dependency where external HTTP calls are needed.
3. Establish dependency manifests and lockfiles using the chosen package-manager conventions. Do not add dependencies speculatively.
4. Implement one validated backend configuration module; centralize environment-variable access.
5. Add `.env.example` with placeholders only, and ignore real environment files, local databases, media, caches, and build output.
6. Add a minimal application entry point, backend/frontend health check, and documented local startup instructions.
7. Configure formatting, linting, type checks, and basic automated test commands using tools supported by the chosen stack.
8. Establish development/test configuration separation. TinyFish must be disabled by default until configured.

### Files or modules likely affected
- `frontend/package.json`, lockfile, Vite and TypeScript configuration.
- `frontend/src/main.tsx`, `frontend/src/app/` or equivalent existing app entry/routing structure.
- `backend/pyproject.toml`, lockfile if used, `backend/app/main.py`, `backend/app/core/config.py`.
- `.env.example`, `.gitignore`, `compose.yaml` where needed, `README.md`.
- Minimal frontend/backend test configuration.

### Dependencies / prerequisites
- Phase 0 completed.
- Tooling versions and local database development method chosen consistently with `ARCHITECTURE.md`.

### Database / API changes
- No business tables or feature endpoints.
- Add only liveness/readiness routes needed to prove that the scaffold starts. Document health checks separately from detector/worker health.

### Tests required
- Frontend production build and TypeScript check.
- Backend import/startup/configuration tests.
- Test that invalid required configuration fails clearly.
- Test that optional TinyFish settings can be absent while the core app starts.
- Verify no real secrets or local media are committed.

### Completion criteria
- A new developer can follow the setup instructions to start the scaffold.
- Frontend build, backend startup, basic checks, and health route succeed.
- Configuration is typed/validated, and no feature code or infrastructure is added prematurely.

---

## Phase 2 — Database Foundation and Initial Migrations

### Goal
Set up durable PostgreSQL persistence and a migration-first schema foundation.

### Features and tasks
1. Configure SQLAlchemy session lifecycle and the repository/data-access boundary.
2. Add the Alembic migration baseline and prove a clean database can be created from migrations.
3. Implement database models and constraints for `users`, `sessions`, `sources`, and `processing_jobs`.
4. Include the documented source context settings (`context_area_label`, `context_retrieval_enabled`, default disabled) and the `context_enrichment` job type from the start.
5. Add shared enums/constants or constrained values for roles, source types/statuses, and job type/status.
6. Implement transaction boundaries, normalized emails, UUID identifiers, timezone-aware timestamps, bounded error summaries, and non-secret JSON validation.
7. Add repository methods for expected access patterns instead of issuing database queries in UI components or scattering raw queries through route handlers.

### Files or modules likely affected
- `backend/app/db/session.py`, `backend/app/db/models.py`.
- `backend/app/repositories/` for users, sessions, sources, and jobs.
- `backend/migrations/` and Alembic configuration.
- `backend/app/core/config.py`.
- `backend/tests/integration/` for schema and repository behavior.

### Dependencies / prerequisites
- Phase 1 configuration and database connectivity.
- `DATABASE.md` constraints and delete rules.

### Database / API changes
- Initial migrations for the foundational tables and indexes.
- Job target constraint must distinguish source-processing, evaluation, and context-enrichment jobs.
- A context-enrichment job requires an authorized source, retrieval enabled, and an approved area label; enforce this cross-record rule in the service and tests.

### Tests required
- Create a clean database from scratch using Alembic.
- Check foreign keys, uniqueness, CHECK constraints, and timezone handling.
- Verify email normalization and session-token-hash storage conventions.
- Verify job target consistency and invalid job/source combinations.
- Verify migrations are repeatable in fresh test environments; do not use production/demo data in destructive tests.

### Completion criteria
- A clean database can be built entirely from migrations.
- The main persistence patterns are tested against PostgreSQL.
- Job types and source settings can support later phases without ad hoc schema edits.

---

## Phase 3 — Backend Core, Sessions, Authorization, and API Conventions

### Goal
Establish a secure API contract and make protected access rules reliable before exposing operational data.

### Features and tasks
1. Add Pydantic request/response schemas and versioned API routing under `/api/v1`.
2. Implement login, logout, current-user, and CSRF handling using server-managed secure sessions as specified.
3. Enforce roles (`operator`, `supervisor`, `technical_admin`) and resource authorization in backend dependencies/service methods.
4. Implement consistent error responses and mapping for validation, authentication, authorization, conflicts, missing resources, dependency failure, rate limits, and internal errors.
5. Add safe structured logging with request correlation IDs; exclude secrets, private media, raw provider bodies, and unnecessary personal data.
6. Add readiness/liveness behavior that distinguishes application availability from database and worker health.
7. Keep generated OpenAPI documentation available for development and appropriately restricted in production.

### Files or modules likely affected
- `backend/app/api/v1/auth.py`, `backend/app/api/v1/system.py`, router registration in `backend/app/main.py`.
- `backend/app/core/security.py`, `backend/app/core/errors.py`, `backend/app/core/config.py`.
- `backend/app/schemas/`, `backend/app/services/auth.py` (or the project's equivalent).
- `backend/app/repositories/users.py`, `backend/app/repositories/sessions.py`.
- `backend/tests/api/`, `backend/tests/unit/`.
- `API.md` only if implementation details expose a necessary contract correction.

### Dependencies / prerequisites
- Phases 1–2.
- A documented decision on demonstration authentication versus fully managed accounts.

### Database / API changes
- Implement documented authentication endpoints, current-user response, session persistence, and health routes.
- No context or incident business endpoints yet.
- Enforce CSRF on cookie-authenticated state-changing requests, safe CORS origins, and appropriate secure-cookie behavior.

### Tests required
- Successful/failed login and logout; expired, revoked, and inactive-user session cases.
- Direct unauthorized endpoint requests and role enforcement.
- CSRF/origin validation and safe error responses.
- Verify passwords, token material, configuration secrets, and raw exceptions never appear in API responses/logs.

### Completion criteria
- Protected endpoints cannot be accessed by bypassing frontend controls.
- Authentication state is server-managed and revocable.
- Errors and logs follow stable, safe conventions.

---

## Phase 4 — Storage Adapter, Source Management, and Background Job Lifecycle

### Goal
Make source creation and long-running processing jobs durable before implementing the detector.

### Features and tasks
1. Implement a private local media-storage adapter for development, using generated storage names and traversal-safe resolution.
2. Add source registration and upload workflow for approved prerecorded clips and clearly labeled simulated sources.
3. Validate file size, allowed type, actual content and decoding feasibility; reject invalid uploads without creating incident conclusions.
4. Implement the PostgreSQL-backed job queue: safe claiming, status transitions, bounded attempts, heartbeat/lease or timeout recovery, and idempotent retry behavior.
5. Define job handlers by type. At this stage, source-processing may be a stub that marks the job's configured outcome explicitly; do not produce simulated success that resembles a real detection.
6. Ensure source/evidence/job records are created transactionally or have a documented recoverable state.
7. Add status endpoints and safe job diagnostics.

### Files or modules likely affected
- `backend/app/api/v1/sources.py`, `backend/app/api/v1/system.py`.
- `backend/app/adapters/storage/`, `backend/app/services/sources.py`.
- `backend/app/processing/jobs.py`, `backend/app/processing/worker.py`.
- `backend/app/repositories/sources.py`, `backend/app/repositories/jobs.py`.
- `backend/app/schemas/sources.py`, `backend/app/schemas/jobs.py`.
- `backend/tests/unit/`, `backend/tests/api/`, `backend/tests/integration/`.

### Dependencies / prerequisites
- Phases 1–3.
- Approved video input mode and sample-data permissions.

### Database / API changes
- Implement documented source list/detail/register/upload/process routes and job-status retrieval.
- Add only migration changes needed to match `DATABASE.md`; do not edit deployed schemas manually.
- Keep API calls short: return 202 and a job ID when processing is queued.

### Tests required
- Upload limits, file/type validation, malicious filename/path handling, and invalid video behavior.
- Transaction rollback or recovery when source/evidence/job creation fails partway through.
- Job claiming, worker crash/recovery, maximum attempts, idempotency, and duplicate submission.
- Authorization on source, evidence metadata, and job resources.
- Confirm a failed job never appears as a successful negative detection.

### Completion criteria
- Valid sources create inspectable records and jobs.
- Invalid files fail safely.
- Jobs can be tracked and recovered without duplicating side effects.
- Media remains private and is never placed in public frontend assets.

---

## Phase 5 — Detector Adapter, Incident Ingestion, Evidence, and Reliability Assessment

### Goal
Deliver a complete backend video-processing path while preserving uncertainty and evidence provenance.

### Features and tasks
1. Use only the pinned YOLOX-S and YuNet adapters for object/face-region observations when configured. These do not classify incidents. Keep event detection unavailable until a compatible event detector and supported category taxonomy are approved; any demonstration flow must remain explicitly DEMO.
2. Define a typed detector interface independent of the model implementation.
3. Decode the approved clip, run supported video-quality checks, and normalize candidate predictions with original score semantics and detector version.
4. Create incident records and associate evidence transactionally/idempotently.
5. Store reliability assessments separately from detector predictions. Implement only approved quality/evidence sufficiency checks and uncertainty reasons.
6. Implement evidence metadata and authorized media-content streaming, including range support when needed by the player.
7. Make processing failures, insufficient evidence, missing media, and successful no-detection outcomes distinguishable.
8. Preserve source-event deduplication so retries do not create duplicate incidents/evidence.

### Files or modules likely affected
- `backend/app/adapters/detectors/`.
- `backend/app/processing/video.py`, worker job handlers.
- `backend/app/services/incidents.py`, `backend/app/services/evidence.py`, reliability assessment service.
- `backend/app/api/v1/incidents.py`, `backend/app/api/v1/evidence.py`.
- `backend/app/schemas/incidents.py`, evidence and assessment schemas.
- `backend/app/repositories/incidents.py`, evidence and assessment repositories.
- `backend/migrations/` and backend tests, if schema details need to be aligned.

### Dependencies / prerequisites
- Phase 4 job/storage workflow.
- Approved detector or simulator, sample permissions, and quality/abstention policy.

### Database / API changes
- Implement incident/evidence/incident-evidence/reliability-assessment schema and the list/detail/content endpoints defined in the specs.
- Ensure a detector prediction cannot be overwritten by a human review.
- Preserve detector name/version/label/score semantics and source timestamp metadata.

### Tests required
- Deterministic detector adapter contract and prediction normalization.
- Decode/inference failure, invalid detector output, no-detection, low-quality, and evidence-insufficient cases.
- Correct evidence/incident association and source-event deduplication.
- Access denial for unauthorized media; media type and byte-range behavior.
- Verify failure is not transformed into a negative detection or confirmed incident.
- Verify no unsupported metric is generated from missing detector output.

### Completion criteria
- A valid clip completes the configured pipeline and makes normalized candidate incidents/evidence inspectable.
- Failure and uncertainty are first-class states.
- Predictions and reliability assessments remain separate and traceable.

---

## Phase 6 — Frontend Foundation and Shared Design System

### Goal
Build the application shell and reusable UI foundations so feature screens remain consistent.

### Features and tasks
1. Implement app routing, authenticated route handling, shared API client, and TanStack Query integration.
2. Implement CSS design tokens for typography, neutral surfaces, borders, spacing, interactive blue, uncertainty amber, and semantic states according to `DESIGN.md`.
3. Build the application shell, navigation, page headers, buttons, form fields, status labels, alert banners, dialogs, tables, pagination, and loading/empty/error patterns.
4. Add accessible focus styles, keyboard support, semantic labels, and status announcements.
5. Clearly identify DEMO/simulated/prerecorded modes where they could otherwise be mistaken for live CCTV.
6. Add consistent API error handling and do not treat every non-2xx response as an identical error.

### Files or modules likely affected
- `frontend/src/main.tsx`, `frontend/src/app/`, `frontend/src/routes/`.
- `frontend/src/api/`, `frontend/src/types/`.
- `frontend/src/components/`, `frontend/src/styles/tokens.css`.
- `frontend/src/features/auth/` and shared state hooks as needed.
- `frontend/tests/` or configured frontend test locations.

### Dependencies / prerequisites
- Phase 1 frontend scaffold.
- `DESIGN.md` token, component, and accessibility requirements.
- API/error conventions from Phase 3.

### Database / API changes
- None. This phase consumes the existing auth and health API contracts.

### Tests required
- TypeScript and production build.
- Navigation and protected-route behavior.
- Shared component states, API error parsing, keyboard focus, labels, and status announcements.
- Responsive shell behavior and no false “live” indicators.

### Completion criteria
- Every page can use a consistent accessible shell and common components.
- Frontend code uses one typed API client and shared server-state conventions.
- No domain workflow is duplicated inside presentational components.

---

## Phase 7 — Incident Review UI and System Status

### Goal
Complete the primary operator workflow end-to-end.

### Features and tasks
1. Implement dashboard summary, incident list filters/sorting/pagination, and incident detail.
2. Build the evidence player/frame view with timestamps, metadata, loading, unavailable, and failed-media states.
3. Build the reliability panel showing only computed assessments, evidence sufficiency, and uncertainty reasons.
4. Add review controls for confirmed by reviewer, false alert, and inconclusive/insufficient evidence.
5. Preserve original detector output visually and in API state; label the review as a human decision.
6. Implement source list/detail and system status, including job status and safe admin diagnostics.
7. Build empty, partial-data, and no-matching-results states rather than placeholders or fabricated dashboard metrics.

### Files or modules likely affected
- `frontend/src/features/dashboard/`.
- `frontend/src/features/incidents/`.
- `frontend/src/features/evidence/`.
- `frontend/src/features/reliability/`.
- `frontend/src/features/sources/`, `frontend/src/features/system-status/`.
- `frontend/src/components/` shared tables, players, status labels, review controls.
- `frontend/tests/` for feature and accessibility behavior.

### Dependencies / prerequisites
- Phases 3, 5, and 6. Backend incident/evidence/review contracts must exist before full UI integration.

### Database / API changes
- Implement the documented dashboard, incidents, evidence, reviews, sources, job, and status endpoints.
- Review create and incident review-status update must commit transactionally and safely handle retry.

### Tests required
- Incident filter/pagination and detail data.
- Evidence loading/authorization errors while keeping incident metadata usable.
- Review success, validation error, retry/deduplication, and persisted state.
- Prediction remains unchanged after review.
- End-to-end primary operator journey using deterministic fixtures.

### Completion criteria
- An authorized operator can sign in, inspect an incident and evidence, see reliability/uncertainty, submit a review, and retrieve the persisted result.
- The UI never labels a detector prediction as a verified crime or hides a processing failure.

---

## Phase 8 — Dataset Evaluation and Reliability Metrics

### Goal
Make reliability claims reproducible and traceable to labeled data.

### Features and tasks
1. Define evaluation dataset and annotation formats, provenance, license/use permissions, and immutable dataset versions.
2. Implement ground-truth event loading and documented event matching.
3. Calculate false alerts per eligible monitored-video hour, precision, recall, detection delay, and review time only where valid duration/timing data exists.
4. Store evaluation runs, metrics, numerator/denominator, units, sample counts, detector/dataset versions, configuration, and unavailability reasons.
5. Keep evaluation jobs on the background worker. Report eligible, excluded, and failed assets independently.
6. Build evaluation create/list/detail APIs and reliability dashboard.
7. Keep benchmark metrics distinct from operational metrics based on human-reviewed incidents.

### Files or modules likely affected
- `backend/app/evaluation/matching.py`, `backend/app/evaluation/metrics.py`.
- `backend/app/api/v1/evaluations.py`, reliability endpoints/services.
- `backend/app/repositories/evaluations.py`, evaluation schemas.
- `backend/migrations/`, `backend/tests/unit/`, `backend/tests/integration/`, `backend/tests/api/`.
- `frontend/src/features/reliability/` and evaluation UI.
- `DATABASE.md`, `API.md`, and `PRD.md` if actual approved contract decisions require amendments.

### Dependencies / prerequisites
- Phases 2, 4, 5, and 6.
- Dataset and ground-truth annotation permissions plus documented matching rules.

### Database / API changes
- Implement evaluation datasets/assets, ground-truth events, evaluation runs, metric results, and linked jobs.
- Undefined metrics must be unavailable/null, never fabricated as zero.
- A completed run is immutable; a new detector/dataset/configuration creates a new run.

### Tests required
- Independently calculated metric fixtures for true/false positives, missed events, event matching, duration denominators, and zero denominators.
- Partial evaluation with failed/excluded samples.
- Reproducibility for identical dataset/model/configuration.
- API authorization and immutable completed-run behavior.
- UI sample counts, units, limitations, and unavailable metric states.

### Completion criteria
- A labeled evaluation completes asynchronously and yields independently verified results.
- Every result is traceable to dataset version, detector version, configuration, and sample counts.
- Contextual web data is never included as detector ground truth by default.

---

## Phase 9 — TinyFish Public Context Enrichment

### Goal
Add best-effort, attributed public-web context without coupling the provider to video inference or human review.

### Features and tasks
1. Implement a typed TinyFish adapter in `backend/app/adapters/integrations/tinyfish.py`, using the backend HTTP client.
2. Before relying on specific response/request fields, verify the [TinyFish Search API reference](https://docs.tinyfish.ai/search-api/reference) and [TinyFish Fetch API reference](https://docs.tinyfish.ai/fetch-api/reference).
3. Implement Search discovery using the approved coarse area label, allowlisted topics, and bounded time window. Do not treat TinyFish Search's `location` as a street-level location; it is a country-code parameter, while the approved area belongs in the query text.
4. Fetch a strictly bounded set of selected public URLs, with markdown output where supported. The provider may accept up to 10 URLs; SafeCity must apply a smaller configured cap.
5. Normalize provider output into typed internal results with title, publisher/domain, original/final URL, short bounded excerpt, topic, publication time when available, retrieval time, freshness status, and safe error metadata.
6. Implement URL policy checks for HTTP(S), embedded credentials, localhost/private/link-local/reserved destinations, and the approved domain policy. Do not let callers submit arbitrary URLs.
7. Implement request timeouts, rate-aware backoff, per-source cooldown, bounded result/excerpt size, deduplication, and idempotent result persistence.
8. Add an authenticated context-list endpoint and context-refresh endpoint that enqueues a `context_enrichment` job and returns 202; keep provider calls out of ordinary request handlers.
9. Preserve existing context items and their original timestamps if a refresh fails. Distinguish empty results, stale/unknown-age results, individual fetch failure, provider error, and disabled configuration.
10. Never send CCTV/video frames, evidence bytes, personal data, credentials, private URLs, or internal-only institutional information to TinyFish.
11. Do not use TinyFish output to create an incident, modify detector scores/reliability metrics, change review outcomes, or initiate alerts/dispatch. Agent/browser automation is out of MVP scope.
12. Keep this integration optional and fail-open for core review workflows: an absent key or provider outage disables context retrieval without blocking the core application.

### Files or modules likely affected
- `backend/app/adapters/integrations/tinyfish.py`.
- `backend/app/services/context.py` and corresponding repository/schema modules.
- `backend/app/processing/jobs.py`, `backend/app/processing/worker.py` and context-enrichment handler.
- `backend/app/api/v1/context.py` or context routes under `sources.py`, following the existing API module convention.
- `backend/app/core/config.py` for `TINYFISH_CONTEXT_ENABLED`, `TINYFISH_API_KEY`, timeout, result cap, TTL, domain allowlist, and refresh cooldown.
- `backend/migrations/` for source context settings, `context_enrichment` job type, and `external_context_items`.
- `backend/tests/unit/`, `backend/tests/api/`, `backend/tests/integration/`.
- `API.md`, `DATABASE.md`, `ARCHITECTURE.md`, `PRD.md`, and `AGENTS.md` only if the implemented contract requires an approved correction.

### Dependencies / prerequisites
- Phases 2–4: source records, configuration, authorization, and the job lifecycle.
- Phase 7 source/system UI contracts for final operator presentation.
- A configured TinyFish API key and approved context-area/topic/domain policy for any live integration test. Ordinary tests must use mocks.

### Database / API changes
- Add/verify the documented source fields `context_area_label` and `context_retrieval_enabled` (default false).
- Permit `context_enrichment` jobs with source_id and no dataset_id.
- Add the `external_context_items` table with source/job references, topic, title, publisher/domain, source URL, bounded summary, published_at nullable, retrieved_at, stale_after, dedupe_key, and safe provider metadata.
- Add authorized GET context list and POST context refresh routes. Do not accept arbitrary external URLs from the browser.
- Do not change incident schemas or detector/evaluation metric meanings.

### Tests required
- Mocked successful Search and Fetch responses with provider schema normalization.
- Empty search, partial Fetch errors, malformed payload, unexpected status, timeout, 401/403, 429/rate limiting, 5xx, and missing key.
- URL policy tests for localhost, private IPs, link-local and metadata targets, file URLs, embedded credentials, unsupported schemes, and domain-policy failures.
- Duplicate-source deduplication, context job retry/idempotency, per-source cooldown, stale/unknown freshness, absent publication time, and preserved timestamps after refresh failure.
- Authorization for source context list/refresh and validation that context retrieval is enabled.
- Security regression tests proving the provider receives no media or personal data.
- Invariant test: external context cannot create incidents, change detector output/reliability metrics, or overwrite review outcomes.
- Verify the core incident/evidence/review workflow still works when TinyFish is disabled or unavailable.
- Network-dependent tests are opt-in and require explicitly configured credentials.

### Completion criteria
- Authorized users can request and view attributed public context for a configured source.
- Context is stored with provenance and clear freshness state and is deduplicated.
- All provider calls occur server-side through bounded worker jobs.
- Empty results and provider failures are distinctly represented; stale items do not appear current.
- The core application remains fully usable when TinyFish is disabled/unavailable.
- No person-identification or automated consequential decision capability is added.

---

## Phase 10 — Dashboard Context UI and Cross-Feature Integration

### Goal
Expose TinyFish context in a calm, evidence-first interface without confusing external context with surveillance evidence.

### Features and tasks
1. Build the shared Public Context panel described in `DESIGN.md`.
2. Show topic, title, publisher/domain, source link, excerpt, publication time when available, retrieval time, and current/stale/unknown state.
3. Keep public context semantically separate from model detections, evidence, assessments, review states, and reliability scores.
4. Add loading, empty, partial, stale, disabled, unavailable, and failed-refresh states.
5. Add the context panel to the source/system view and, where the source association makes sense, the incident detail view. Do not make it look causally linked to an incident unless that relationship is explicitly supported.
6. Make source links keyboard accessible, safely open external pages, and clearly indicate leaving SafeCity AI.
7. Ensure contextual content cannot visually change the severity/status presentation of a detector-generated incident.

### Files or modules likely affected
- `frontend/src/features/sources/`, `frontend/src/features/system-status/`.
- `frontend/src/features/incidents/` only for an appropriate source-level context view.
- `frontend/src/components/PublicContextPanel.tsx` (or established equivalent), shared status/alert components.
- `frontend/src/api/` and `frontend/src/types/` for typed context endpoints.
- `frontend/tests/` for component, accessibility, and API-failure behavior.
- `DESIGN.md` or `API.md` only for approved contract adjustments.

### Dependencies / prerequisites
- Phases 6–9.

### Database / API changes
- No new schema is expected if Phase 9 follows the documented contract.
- Only amend API fields if implementation reveals a genuine discrepancy; update frontend types and contract tests in the same change.

### Tests required
- Correct rendering of source provenance and timestamp states.
- Safe external link behavior and keyboard accessibility.
- Empty/disabled/unavailable/stale/partial context states.
- Confirmation that context styling does not imply verified danger or alter incident/review state.

### Completion criteria
- Users can inspect public context and its origin without losing the current incident/source context.
- The panel clearly explains stale or unknown data and never blocks evidence review.

---

## Phase 11 — End-to-End Validation, Security Review, and Demo Readiness

### Goal
Verify the documented MVP workflow across the frontend, API, database, worker, media storage, evaluation, and TinyFish adapter.

### Features and tasks
1. Run the whole local startup sequence from a clean checkout using documented migrations and environment setup.
2. Seed only deterministic demo users/sources/incidents with clearly labeled simulated/prerecorded data; make seed operations idempotent.
3. Execute the primary acceptance journey: sign in, inspect incident/evidence, review uncertainty, save a human outcome, and retrieve it.
4. Execute a labeled evaluation and compare returned metrics with independently calculated expectations.
5. Execute the public-context journey with mocked provider results, then optionally with TinyFish credentials in a deliberately opted-in integration environment.
6. Verify provider outages and failed video processing do not create false confirmed incidents or make unrelated features unavailable.
7. Run lint, formatting, TypeScript checks, production frontend build, backend unit/API/integration tests, migration tests, and applicable accessibility/security checks.
8. Review final changes for secrets, unsafe URLs, unexpected external requests, unbounded result sets, privacy/retention issues, and mismatches between the six specs and actual behavior.
9. Document known limitations, unresolved decisions, setup commands, and the difference between simulated data and any real integration tested.

### Files or modules likely affected
- `backend/tests/`, `frontend/tests/`, test fixtures and approved seed scripts.
- `scripts/seed_demo_users.py` (or the documented equivalent).
- `README.md`, `.env.example`, CI configuration if present.
- Source documents only if an actual implementation-approved contract change is needed.

### Dependencies / prerequisites
- Phases 1–10.
- An environment with PostgreSQL and approved test data.
- TinyFish key only for an explicitly enabled external integration test; mocked tests remain the default.

### Database / API changes
- No planned feature schema or endpoint additions.
- Any migration or contract fix must be added through a reviewed migration/spec update, not an ad hoc production change.

### Tests required
- All project unit, API, database integration, frontend, evaluation, and end-to-end tests.
- Authentication/RBAC/CSRF, evidence authorization, upload validation, source-event deduplication, job recovery, and safe error tests.
- TinyFish URL/data boundary, failure isolation, provenance, freshness, and no-influence-on-detection/review tests.
- Clean-install/recovery verification to the extent supported by the development environment.

### Completion criteria
- The core operator workflow works from a clean setup.
- Migrations apply, critical tests pass, and evaluation figures match independent calculations.
- TinyFish works through the approved test path or is accurately identified as not externally verified.
- No secret/private media leaks; no unsupported safety or performance claims are made.
- Any checks not run and any unresolved blockers are reported explicitly.

---

## Recommended First Task

**Task 1 — Bootstrap the repository and validate the local development loop.**

Create the minimal React/TypeScript/Vite frontend and FastAPI/Python 3.12 backend scaffolds; configure dependency manifests, validated backend settings, `.env.example`, `.gitignore`, health checks, and basic lint/type/test commands. Do not build feature screens, video inference, or TinyFish calls in this task. Completion is a clean setup in which the frontend builds, the backend starts with valid placeholder configuration, tests run, and no secrets or media are committed.

Once that task is verified, proceed to the initial PostgreSQL/Alembic migration in Phase 2.
