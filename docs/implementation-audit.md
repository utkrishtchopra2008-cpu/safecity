# Implementation audit and traceability

Audit reviewed against local tree `76b898dacca311c64776084b69067f79190da623` and remote `main` HEAD `420197b2cb491108d63053a858ab621beae44371` on 2026-10-23. The local branch is `main`, one local commit ahead of its cached `origin/main` (`f799344`); the GitHub remote has advanced to `420197b`, a GitHub API-created documentation commit with the same inspected tree state. The local remote-tracking ref cannot be refreshed by the shell in this environment, so do not treat it as current remote state. Product requirements come from `PRD.md`, `ARCHITECTURE.md`, `DATABASE.md`, `API.md`, `DESIGN.md`, and `IMPLEMENTATION_PLAN.md`; `README.md` is evidence about current implementation, not authority for requirements. The repository implements selected workflows but remains partial against contracts. Finding statuses use `CONFIRMED`, `NOT PRESENT`, `PARTIAL`, and `UNVERIFIED`; requirement proofs use `PASS`, `PARTIAL`, `BLOCKED`, `NOT RUN`, or `FAIL`. “NOT PRESENT” means no implementation was found in the inspected tree; it does not imply an unsafe runtime defect.

## Repository and environment

| Finding | Status | Evidence |
|---|---|---|
| Checkout and working tree | CONFIRMED | Prompt 0 began clean on `main` at `f799344`; its documentation change is local commit `76b898d`. Before Prompt 1, there were no working-tree edits. |
| Prompt 1 local/remote Git state | CONFIRMED | Local `main` at `76b898dacca311c64776084b69067f79190da623`, clean before Prompt 1 docs, `main...origin/main [ahead 1]`; GitHub `main` at `420197b2cb491108d63053a858ab621beae44371`. See local status and GitHub commit URL below. Shell remote transport is unavailable; the GitHub connector verified remote state. |
| Remote and recent history | CONFIRMED | `origin` fetch/push URL is `https://github.com/utkrishtchopra2008-cpu/safecity.git`. Remote `main` recent commits: `420197b` documentation state; `f799344` README; `1aa3587` dashboard filters; `a2c5e37` incident filters/pagination; `4d43bb0` review response tests; `60ad489` demo video; `485c84c` technical-admin job diagnostics; `650aa4f` supervisor status. The local `git log` has same history through `f799344` and Prompt 0 local commit `76b898d`. |
| Specifications | PASS | All six authority documents and `AGENTS.md` present at repository root. |
| Frontend foundation | PARTIAL | `frontend/src/app/router.tsx` and pages for login, dashboard, incidents, reliability, evaluations, system status, and setup implement selected workflows. Technical-admin source registration/upload controls are in `frontend/src/components/SourceAdminPanel.tsx`; `frontend/src/components/SourceAdminPanel.test.tsx` covers DEMO registration, upload/results, and storage failure. Full interaction/accessibility coverage is absent. |
| Backend foundation | PARTIAL | `backend/app/main.py`, `backend/app/core/config.py`; liveness and DB-probing readiness exist. Worker health is honestly `not_running`; storage readiness is configuration-only. |
| Persistence | PARTIAL | `backend/app/db/models.py` defines the required entities and `backend/migrations/versions/0001_initial_schema.py` adds the schema. A disposable PostgreSQL migration/constraint/rollback integration run passed earlier in this work session; the optional test skips when `SAFECITY_TEST_DATABASE_URL` is unset. |
| CI and dependency lockfiles | PARTIAL | `.github/workflows/ci.yml`, `frontend/package-lock.json`, and `backend/uv.lock` are present. CI runs frontend lint/format/typecheck/tests/build and backend Ruff/format/mypy/pytest. The frontend CI install uses `npm ci`; backend install uses `uv sync --locked`. The exact-SHA combined status query for remote HEAD `420197b` returned no status entries. The connector's workflow-run lookup is limited to PR-triggered runs; the public Actions feed's latest listed run is #40 on `485c84c`, not current HEAD. No current-HEAD run is visible in the inspected feed, so its Actions result is NOT VERIFIED. |
| Compose | PARTIAL | `compose.yaml` defines PostgreSQL, backend, and a single worker service. Worker health reporting and full container startup were not verified. |
| Environment | PARTIAL | `.env.example` now includes backend-only Supabase Storage placeholders and upload byte/duration limits; actual credentials and deployment policy are unavailable. |
| Runtime | PARTIAL | Current shell reports Node `v24.22.0`, Python `3.14.7`, Docker `29.8.2`, Compose `v5.6.0`; `uv` is not on the current shell PATH. Backend requires Python `>=3.12,<3.13`, frontend requires Node `>=22.12,<23`. Prompt 0 `make check` previously ran in the selected compatible environment (Python 3.12.14, Node 22.16.0); this environment's Compose services were not started during Prompt 1. |
| Automated tests | PARTIAL | Prompt 0 `make check`: backend 100 passed, 3 skipped; frontend 16 passed. Two model tests skipped because verified local artifacts are not configured; the PostgreSQL test skipped because `SAFECITY_TEST_DATABASE_URL` is unset. These checks do not establish live Supabase/TinyFish behavior or full PRD acceptance. |

## Risk-ranked gap register

Priority definition: P0 = safety, privacy, authorization, or correctness risk that can expose evidence or mislead an operator; P1 = mandatory MVP workflow/contract gap; P2 = operational hardening or optional improvement after P0/P1. The repository has no optional product scope that should displace unresolved mandatory MVP requirements.

| Priority | Finding | Status | Required proof |
|---|---|---|---|
| P0 | Authentication, authorization, CSRF, resource-level evidence access | PARTIAL | `backend/app/api/v1/auth.py` implements server sessions/CSRF/roles; `backend/app/api/v1/evidence.py` limits metadata/content to operator/supervisor roles and issues 120-second signed redirects with audit events. Incident/evidence authorization remains role-level because no tenant/source membership model exists; live object access is unverified. |
| P0 | Upload validation, private media storage, streaming byte caps, decode/corruption handling | PARTIAL | `backend/app/api/v1/sources.py` uses `backend/app/media/uploads.py` and `backend/app/storage/supabase.py` to accept validated files and create source/evidence/job records. A generated AVI passed OpenCV upload/quality sampling; `backend/tests/test_video_uploads.py` now fault-injects decoder-open, invalid metadata, excessive dimensions/duration, and no-frame failures. Broader real-codec/corrupt-file matrix and live Supabase remain unverified. |
| P1 | Authoritative SQL schema, migrations, transaction/idempotency guarantees | PARTIAL | SQLAlchemy models and an initial revision now exist; a disposable PostgreSQL migration/constraint/duplicate-ingestion/rollback run passed earlier in this work session. Live Supabase remains unverified; the optional PostgreSQL test is skipped without its configured URL. |
| P1 | Job queue/worker, recovery, bounded retries, cancellation, orphan cleanup | PARTIAL | `backend/app/worker.py` atomically claims PostgreSQL jobs, recovers expired leases, retries bounded transient Storage failures, performs bounded OpenCV quality sampling, and dispatches context jobs to `backend/app/services/context_jobs.py`. `backend/app/cli/cleanup_orphan_storage.py` provides explicit dry-run-first orphan cleanup with reference rechecks; live Supabase validation and dead-letter administration remain absent/unverified. Cancellation is deliberately unimplemented because `API.md` §4.7 and `DATABASE.md` §4.5 define no cancellation route/state or transition semantics; see `docs/implementation-decisions.md`. |
| P1 | Required API endpoint catalogue and typed schemas | PARTIAL | Typed auth, dashboard, incident/review, evidence metadata/content, source list/detail/create/upload/reprocess/context-list/context-refresh, public Search/Fetch, job status, system summary, reliability summary, and evaluation list/detail/create routes are registered. Evaluation creation currently returns `DETECTOR_UNAVAILABLE` because no verified detector handler is installed. |
| P1 | Incident workflows, human review, metric correctness and evaluation provenance | PARTIAL | `backend/app/services/incidents.py` supports filtered listing and atomic review persistence; `backend/app/api/v1/reliability.py` only surfaces persisted completed labeled-evaluation metrics and explicit unavailable values. `backend/app/services/evaluation_metrics.py` has bounded hand-fixture-tested calculations; evaluation creation is detector-blocked and the calculator is not connected to run persistence. |
| P1 | Required screens and loading/empty/error/uncertain states | PARTIAL | Login, dashboard, incident list/detail/review with evidence playback, reliability summary, evaluation runs, public search, source context, system/source status, setup, and technical-admin source registration/upload views exist. Source upload/result states have focused component coverage; comprehensive transition coverage and visual/accessibility review remain absent. |
| P1 | Supabase storage policy/RLS and backend authorization boundary | PARTIAL | `docs/supabase-storage.md` specifies a private bucket and deny-by-default direct-user policies; the adapter uses a server-side service-role credential and evidence/source routes perform backend role checks. Source/tenant membership authorization is limited by the schema, and live policies were not applied. |
| P1 | TinyFish safe boundary, provenance, freshness, timeout/degradation | PARTIAL | `backend/app/services/tinyfish.py` implements bounded Search and selected-result Fetch; source-level context routes enqueue a deduplicated PostgreSQL job handled by `backend/app/services/context_jobs.py`. Allowlisted domains, bounded streamed responses, query privacy checks, final-URL validation, attribution/freshness, capped work and cooldowns are implemented. Mocks cover provider boundaries; live provider verification and fully role/source-scoped tenancy remain unverified. |
| P2 | Structured sanitized logs, correlation, readiness by dependency, audit trail | PARTIAL | `backend/app/main.py` adds request IDs, redacted error handling and a database readiness probe; `backend/app/services/audit.py` writes append-only events for auth/reviews/source creation. Storage/worker probes and broader security-action coverage remain absent. |
| P2 | CI reproducibility, release/rollback, backups/retention configuration | PARTIAL | GitHub Actions uses committed frontend/Python lockfiles. Run #40 passed on older `485c84c`; current remote HEAD has no visible run/status. Backup/restore and release rollback drills are absent; retention remains approval-dependent. |
| P1 | Approved incident/event detector, supported event taxonomy, and labeled evaluation dataset | NOT PRESENT | YOLOX-S INT8BQ and YuNet provide object and face-region observations only (`docs/model-artifacts.md`, `backend/app/services/opencv_models.py`); neither is an event detector. No compatible approved event classifier or labeled dataset is present, so event prediction and detector-backed evaluation remain unavailable. |

Cross-cutting checks: implementation remains materially narrower than the product contracts. `AGENTS.md` defines scope but there is no `CODEOWNERS`; auth, incident/review, source registration/upload, job status, evidence, dashboard/system summary, reliability/evaluation reads, and public-context Search/Fetch/source refresh routes exist. Admins can register clearly labelled simulated sources and submit prerecorded uploads through the system screen; `backend/app/cli/seed_demo.py` also provides one explicit deterministic synthetic fixture for local walkthroughs. Upload staging is byte-bounded and OpenCV checks metadata/first-frame decoding; the worker samples bounded quality and optional pinned YOLOX/YuNet observations, but full corruption/codec precision and production resource-time characterization are not established. Model taxonomy/version/license/checksum provenance is recorded; no supported event detector is configured and object observations do not create incidents. Migrations and a disposable PostgreSQL integrity run exist; live Supabase RLS was not applied. Sessions, expiry/revocation checks, CSRF, login/source/upload/processing/evaluation rate limits, redacted API errors, correlation IDs, DB audit and one PostgreSQL worker exist; limits are process-local, while source/tenant-level evidence authorization, cancellation, full operational logging, and worker liveness reporting remain incomplete. `backend/app/cli/cleanup_orphan_storage.py` provides a bounded explicit dry-run/apply cleanup for old unreferenced generated uploads; it has not run against live Supabase. `docs/threat-model.md` maps tested controls and known deployment limits. TinyFish is optional and mocked, with a per-process search cooldown and database-backed source refresh; cross-process public-search rate coordination and live provider verification remain absent. Retention remains non-destructive/configurable. Detector-backed evaluation, comprehensive source-management controls, visual/a11y review, backup/restore and release rollback drills remain absent or unverified. CI is present and lockfile-based; local backend/frontend verification passed. No event detection or event-reliability claim is generated.

## Requirement-to-file/test trace

| Contract group | Authority | Implementation now | Required implementation/proof |
|---|---|---|---|
| PRD goals, non-goals, journeys, FR 6.1–6.8, acceptance AT-01–AT-15 | `PRD.md` §§2,4–8,14,16 | Auth, incident/review, source intake, reliability display, and selected frontend workflows exist; acceptance coverage remains partial. | Add the missing processing/evaluation journeys and AT-specific route/service tests. Preserve no identity tracking, risk scoring, accusation, punishment or dispatch. |
| Auth, dashboard, incident, review, evidence, source/upload, jobs/status, reliability, evaluations, public context, errors, paging, limits | `API.md` §§3–14 | Auth/dashboard/incidents/reviews/evidence/source list/detail/register/upload/reprocess/context-list/context-refresh, jobs/system summary, reliability summary, evaluation list/detail/create, and TinyFish public Search/Fetch are typed under `backend/app/api/v1/`; evaluation creation is blocked by the missing verified detector. Tenant/source membership authorization and broader negative contract tests remain incomplete. | OpenAPI comparison and role/source authorization tests. |
| Schema entities, constraints, indexes, deletion rules and ownership | `DATABASE.md` §§4–10,13–14 | `backend/app/db/models.py`; initial revision `backend/migrations/versions/0001_initial_schema.py` | Disposable PostgreSQL fresh/roundtrip migration, constraint, duplicate-ingestion and rollback checks ran earlier in this session; live Supabase policies remain NOT RUN. |
| Pages, component system, states, responsiveness, accessibility | `DESIGN.md` §§6–18; `PRD.md` §§8,13 | Login, dashboard, incident list/detail with evidence playback, reliability, evaluations, system/source status, setup, and technical-admin source registration/upload pages. `frontend/src/components/SourceAdminPanel.test.tsx` covers registration, upload/result, and storage-error states. | Comprehensive page-state, keyboard, viewport and contrast review. |
| Modular architecture, worker, storage, security, observability, deployment acceptance | `ARCHITECTURE.md` §§4–23 | SQLAlchemy data layer, private Supabase Storage adapter, DB worker, auth/security middleware, audit events and readiness probe; worker liveness is not reported | Broader operational/security tests, live storage policy validation, monitoring, migration/release checks. |
| Audit/implementation plan | `IMPLEMENTATION_PLAN.md` | The plan was drafted before current implementation; its planning intent is preserved and its stale “documentation-only” premise was corrected in Prompt 0. It remains a planned phase checklist, not proof of present status. | Use the current evidence and status in this audit. Prompt 2 has now been audited and implemented to its available local verification boundary; follow the next supplied prompt and do not infer missing prompt scope. |

## Execution sequence and gates

1. Schema and persistence: exact `DATABASE.md` models, Alembic and backend-only configuration; fresh PostgreSQL migration, rollback, duplicate and integrity tests passed in the disposable DB run. Live Supabase remains unverified.
2. Storage and upload/video safety: private adapter, streaming checks and OpenCV opening/first-frame validation; endpoint now queues a processing job. Optional pinned YOLOX/YuNet CPU observations run only when configured; they do not produce event categories. A bounded explicit orphan-cleanup CLI is covered with mocks; live storage, broader codec/corruption matrix and cleanup against a configured project remain unverified. Incident/event detection is still blocked on a compatible licensed model and labeled data.
3. Auth/security and typed API: server sessions, CSRF and partial role checks implemented; route catalogue and object-level scopes remain incomplete. Gate: broader negative access and schema tests.
4. Worker, review, evaluation and observability: Postgres-backed jobs and reproducible measured metrics; gate: retries/recovery/rollback and metric fixtures.
5. Frontend and optional TinyFish: required screens first; provider remains optional, mocked in CI; gate: frontend checks and honest DEMO/unavailable states.
6. Full verification and release notes: run only checks supported by available runtimes/services; report unavailable checks as NOT RUN/BLOCKED.

Change scope is reversible and additive: migrations only, no destructive data changes, no real secrets or media. Primary conflict risk is shared contract/schema work; keep API/database/auth/video/frontend boundaries in their existing directories. Optional improvements are deferred; all PRD “must have” capabilities remain mandatory. Rollout requires backups, explicit migration, configured secrets and rollback to the prior app revision; no calendar estimate is asserted.

## Detailed acceptance trace

Statuses below describe implemented proof, not a claim that the entire parent requirement is complete. Where a detector or approved labeled dataset is absent, the safe behavior is explicitly unavailable and the listed test proves that boundary.

### PRD functional requirements and acceptance tests

| Requirement | Status | Implementation and proof / remaining gate |
|---|---|---|
| FR-001–003 controlled access, roles, backend enforcement | PARTIAL | `backend/app/api/v1/auth.py`, `backend/app/api/v1/evidence.py`, `backend/app/main.py`; `backend/tests/test_auth.py`; broader role/resource negative matrix remains. |
| FR-004–008 candidate intake, normalization, validation, duplicates, processing status | PARTIAL | `backend/app/api/v1/sources.py`, `backend/app/services/incidents.py`, `backend/app/worker.py`, `backend/app/db/models.py`; `backend/tests/test_postgres_integrity.py`, `backend/tests/test_video_uploads.py`, `backend/tests/test_worker.py`; no genuine event detector is configured. |
| FR-009–015 measured quality, assessment, sufficiency, uncertainty, semantics, safe conclusions | PARTIAL | `backend/app/worker.py`, `backend/app/services/opencv_models.py`, `backend/app/db/models.py`; `backend/tests/test_opencv_models.py`, `backend/tests/test_worker.py`; insufficient-event evidence behavior and detector-driven abstention need an approved detector contract. |
| FR-016–020 evidence association, missing/integrity/explanation/access | PARTIAL | `backend/app/api/v1/evidence.py`, `backend/app/api/v1/incidents.py`, `backend/app/storage/supabase.py`, `backend/app/db/models.py`; `backend/tests/test_auth.py`, `backend/tests/test_supabase_storage.py`; live Supabase and complete source-level authorization remain unverified. |
| FR-021–027 incident list/detail/filter/review/prediction separation/notes/history | PARTIAL | `backend/app/services/incidents.py`, `backend/app/api/v1/incidents.py`, `frontend/src/pages/IncidentsPage.tsx`, `frontend/src/pages/IncidentDetailPage.tsx`; `backend/tests/test_auth.py`; notes/history fields are present, but full route/state-specific test coverage is incomplete. |
| FR-028–034 metrics, definitions, labeled evaluation, metadata, breakdowns, comparisons, source labeling | PARTIAL | `backend/app/services/evaluation_metrics.py`, `backend/app/api/v1/evaluations.py`, `backend/app/api/v1/reliability.py`, `frontend/src/pages/EvaluationsPage.tsx`, `frontend/src/pages/ReliabilityPage.tsx`; `backend/tests/test_evaluation_metrics.py`; dataset-backed execution and comparison/breakdown are unavailable until approved fixtures and event detector exist. |
| FR-035–037 source status, failures, demo identification | PARTIAL | `backend/app/api/v1/sources.py`, `backend/app/api/v1/jobs.py`, `frontend/src/pages/SystemStatusPage.tsx`, `frontend/src/components/SourceAdminPanel.tsx`; `backend/tests/test_worker.py`, `frontend/src/components/SourceAdminPanel.test.tsx`; worker liveness is reported unavailable. |
| FR-038–044 public context, attribution/freshness/separation/bounds/degradation/privacy | PARTIAL | `backend/app/services/tinyfish.py`, `backend/app/services/context_jobs.py`, `backend/app/api/v1/public_context.py`, `backend/app/api/v1/sources.py`, `frontend/src/pages/PublicContextPage.tsx`, `frontend/src/pages/SourceContextPage.tsx`; `backend/tests/test_tinyfish.py`, `backend/tests/test_context_jobs.py`; live provider and cross-process search rate coordination remain unverified/incomplete. |
| AT-01 ingestion; AT-02 duplicate handling | PARTIAL | `backend/app/services/incidents.py`, `backend/app/db/models.py`; `backend/tests/test_postgres_integrity.py`; database integration requires disposable PostgreSQL. |
| AT-03 correct evidence; AT-04 missing evidence | PARTIAL | `backend/app/api/v1/evidence.py`, `frontend/src/pages/IncidentDetailPage.tsx`; `backend/tests/test_auth.py`; live storage authorization remains unverified. |
| AT-05 quality warning; AT-06 uncertainty | PARTIAL | `backend/app/worker.py`, `backend/app/db/models.py`; `backend/tests/test_opencv_models.py`, `backend/tests/test_worker.py`; no event-classifier uncertainty policy is configured. |
| AT-07 persisted review; AT-08 prediction/review separation | PARTIAL | `backend/app/services/incidents.py`, `backend/app/db/models.py`, `frontend/src/pages/IncidentDetailPage.tsx`; `backend/tests/test_auth.py` now verifies review response shape and session-derived reviewer; database-backed atomic persistence/rollback and full API matrix remain. |
| AT-09 metric correctness; AT-10 insufficient data | PARTIAL | `backend/app/services/evaluation_metrics.py`; `backend/tests/test_evaluation_metrics.py`; currently pure fixture calculations, not persisted detector evaluation runs. |
| AT-11 direct evidence access control | PARTIAL | `backend/app/api/v1/evidence.py`, `backend/app/main.py`; `backend/tests/test_auth.py`; live signed Storage URL check unavailable. |
| AT-12 invalid video failure without positive conclusion | PARTIAL | `backend/app/media/uploads.py`, `backend/app/worker.py`; `backend/tests/test_video_uploads.py`, `backend/tests/test_worker.py`; broaden codec/corruption coverage. |
| AT-13 demo integrity | PARTIAL | `frontend/src/components/SourceAdminPanel.tsx`, `frontend/src/pages/SystemStatusPage.tsx`, `backend/app/api/v1/sources.py`, `backend/app/cli/seed_demo.py`; `frontend/src/components/SourceAdminPanel.test.tsx`, `backend/tests/test_seed_demo.py`; fixture command is synthetic and dev/test-only, while broader browser journey remains unverified. |
| AT-14 context provenance/failure isolation; AT-15 provider data boundary | PARTIAL | `backend/app/services/tinyfish.py`, `backend/app/services/context_jobs.py`; `backend/tests/test_tinyfish.py`, `backend/tests/test_context_jobs.py`; tests use mocks, no live TinyFish request. |

### API, database, design and architecture contract trace

| Contract area | Status | Implementation and proof / remaining gate |
|---|---|---|
| API auth: login/logout/current user | PARTIAL | `backend/app/api/v1/auth.py`, `backend/app/api/v1/schemas.py`; `backend/tests/test_auth.py`; compare all response/error branches with `API.md` contract tests. |
| API dashboard | PARTIAL | `backend/app/api/v1/dashboard.py`; route registered in `backend/app/api/v1/router.py`; route-specific contract test coverage is incomplete. |
| API incidents list/detail/review | PARTIAL | `backend/app/api/v1/incidents.py`, `backend/app/services/incidents.py`; `backend/tests/test_auth.py`, `frontend/src/pages/IncidentsPage.test.tsx`; frontend request encoding/page transitions are covered, while backend result filtering, detail provenance, and role matrix remain. |
| API evidence metadata/content | PARTIAL | `backend/app/api/v1/evidence.py`; `backend/tests/test_auth.py`, `backend/tests/test_supabase_storage.py`; live playback and storage policy checks remain. |
| API sources register/upload/detail/reprocess/context | PARTIAL | `backend/app/api/v1/sources.py`; `backend/tests/test_video_uploads.py`, `backend/tests/test_context_jobs.py`; comprehensive typed response tests and live storage remain. |
| API jobs/status/health | PARTIAL | `backend/app/api/v1/jobs.py`, `backend/app/main.py`, `backend/app/worker.py`; `backend/tests/test_worker.py`, `backend/tests/test_health.py`; no cancel endpoint/state is specified in `API.md`, so none was invented. |
| API reliability/evaluations | PARTIAL | `backend/app/api/v1/reliability.py`, `backend/app/api/v1/evaluations.py`; `backend/tests/test_evaluation_metrics.py`; detector-backed evaluation is intentionally unavailable. |
| API TinyFish Search/Fetch | PARTIAL | `backend/app/api/v1/public_context.py`, `backend/app/services/tinyfish.py`; `backend/tests/test_tinyfish.py`; provider integration uses mocked tests; live secret/provider not configured. |
| `POST /api/v1/auth/login` | PARTIAL | `backend/app/api/v1/auth.py`; `backend/tests/test_auth.py` generic failure, rate limit and cookie secrecy; successful flow tested. |
| `POST /api/v1/auth/logout` | PARTIAL | `backend/app/api/v1/auth.py`; `backend/tests/test_auth.py` CSRF and revocation; tested. |
| `GET /api/v1/auth/me` and `GET /api/v1/auth/csrf` | PARTIAL | `backend/app/api/v1/auth.py`; `backend/tests/test_auth.py` expiry/revocation/CSRF; tested. |
| `GET /api/v1/dashboard/summary` | PARTIAL | `backend/app/api/v1/dashboard.py`, `frontend/src/pages/DashboardPage.tsx`; `frontend/src/pages/DashboardPage.test.tsx` verifies date/source query encoding and inverted-range handling; backend response aggregation and range validation tests remain. |
| `GET /api/v1/incidents` | PARTIAL | `backend/app/api/v1/incidents.py`, `backend/app/services/incidents.py`, `frontend/src/pages/IncidentsPage.tsx`; `frontend/src/pages/IncidentsPage.test.tsx` verifies query encoding and page transitions; backend filtered-result/paging response tests remain. |
| `GET /api/v1/incidents/{incident_id}` | PARTIAL | `backend/app/api/v1/incidents.py`; current test suite lacks full detail/provenance response contract assertions. |
| `POST /api/v1/incidents/{incident_id}/reviews` | PARTIAL | `backend/app/api/v1/incidents.py`, `backend/app/services/incidents.py`; `backend/tests/test_auth.py` verifies typed success, allowed outcome/note, and server-derived reviewer identity; transactional persistence, duplicate conflict, and rollback still need PostgreSQL route tests. |
| `GET /api/v1/incidents/{incident_id}/reviews` | PARTIAL | `backend/app/api/v1/incidents.py` implements authenticated review-history retrieval; `backend/tests/test_auth.py` now verifies the typed history response. Resource-scope authorization and database-backed route coverage remain limited by the absence of a membership model. |
| `GET /api/v1/evidence/{evidence_id}` and `/content` | PARTIAL | `backend/app/api/v1/evidence.py`; unauthenticated denial and adapter signing tests exist; successful authorized resource access is not covered end-to-end. |
| `GET /api/v1/sources` and `GET /api/v1/sources/{source_id}` | PARTIAL | `backend/app/api/v1/sources.py`; `backend/tests/test_auth.py` now proves an authenticated operator receives an empty list and an unknown source gets the standardized 404; non-empty field serialization and broader visibility tests remain. |
| `POST /api/v1/sources` | PARTIAL | `backend/app/api/v1/sources.py`; `backend/tests/test_auth.py` proves operator denial; admin success response and audit coverage remain incomplete. |
| `POST /api/v1/sources/upload` | PARTIAL | `backend/app/api/v1/sources.py`, `backend/app/media/uploads.py`; streaming/signature tests exist; full route transaction/storage failure tests remain. |
| `POST /api/v1/sources/{source_id}/process` | PARTIAL | `backend/app/api/v1/sources.py`, `backend/app/worker.py`; current route coverage verifies auth; reprocess success/idempotency contract needs route tests. |
| `GET /api/v1/sources/{source_id}/context`, `POST .../context-refresh` | PARTIAL | `backend/app/api/v1/sources.py`, `backend/app/services/context_jobs.py`; `backend/tests/test_context_jobs.py` covers both simulated and uploaded source context enrichment with database dedupe; route role/resource success cases remain. |
| `GET /api/v1/jobs/{job_id}` and `/api/v1/system/status` | PARTIAL | `backend/app/api/v1/jobs.py`; `backend/tests/test_auth.py` covers operator access to an owned job, uniform not-found for another user's and missing jobs, diagnostic/private-key redaction, non-privileged operator status, supervisor aggregate counts/degraded state, and technical-admin diagnostic access without ownership; additional source/job count variations remain. |
| `GET /health/live` and `/health/ready` | PARTIAL | `backend/app/main.py`; `backend/tests/test_health.py` covers liveness and configuration/database readiness; storage reports configuration, worker liveness remains `not_reported`, and optional provider reports configured/disabled rather than live verification. |
| `GET /api/v1/reliability/summary` | PARTIAL | `backend/app/api/v1/reliability.py`; metric service tests verify definitions; route filters/response-source contract tests remain. |
| `GET /api/v1/evaluations`, `GET /api/v1/evaluations/{evaluation_id}` | PARTIAL | `backend/app/api/v1/evaluations.py`; current route test proves auth gate; authorized pagination/detail response tests remain. |
| `POST /api/v1/evaluations` | PARTIAL | `backend/app/api/v1/evaluations.py`; safe `DETECTOR_UNAVAILABLE` path exists; supported detector-backed evaluation creation is unavailable until approved model/data exist. |
| `POST /api/v1/public-context/search` and `/fetch` | PARTIAL | `backend/app/api/v1/public_context.py`, `backend/app/services/tinyfish.py`; mocked route/provider and boundary tests exist; live provider remains unverified and rate cooldown is process-local. |
| Database entities `users`, `sessions`, `sources`, `evaluation_datasets`, `processing_jobs`, `incidents`, `evidence`, `incident_evidence`, `reliability_assessments`, `reviews`, `evaluation_assets`, `ground_truth_events`, `evaluation_runs`, `metric_results`, `external_context_items`, `audit_events` | PARTIAL | `backend/app/db/models.py`, `backend/migrations/versions/0001_initial_schema.py`; `backend/tests/test_postgres_integrity.py`; fresh/upgrade/downgrade/invariant tests ran against disposable PostgreSQL earlier; hosted Supabase not run. |
| Database key constraints, indexes, FKs, state/interval/count/uniqueness rules | PARTIAL | `backend/app/db/models.py`, `backend/migrations/versions/0001_initial_schema.py`; `backend/tests/test_postgres_integrity.py`; no live Supabase migration validation. |
| Database deletion, ownership, prediction/review/context separation, audit immutability | PARTIAL | `backend/app/db/models.py`, migration, `backend/app/services/audit.py`; `backend/tests/test_postgres_integrity.py`; approval-dependent retention remains configurable and non-destructive. |
| Storage object inventory/orphan cleanup without unexpected evidence deletion | PARTIAL | `backend/app/storage/supabase.py`, `backend/app/services/storage_cleanup.py`, `backend/app/cli/cleanup_orphan_storage.py`; `backend/tests/test_supabase_storage.py`, `backend/tests/test_storage_cleanup.py` cover bounded listing, missing-reference reporting, old/unreferenced filtering, recursion and reference recheck. The command is dry-run by default and requires an explicit operator-selected age and `--apply`; live Supabase cleanup is NOT RUN. |
| Design pages: login, dashboard, incident list/detail, reliability, system/sources, evaluation | PARTIAL | `frontend/src/pages/LoginPage.tsx`, `DashboardPage.tsx`, `IncidentsPage.tsx`, `IncidentDetailPage.tsx`, `ReliabilityPage.tsx`, `SystemStatusPage.tsx`, `EvaluationsPage.tsx`; `frontend/src/app/router.tsx`; page-specific visual acceptance review not run. |
| Design states: loading, empty, error, failed, unavailable, uncertain | PARTIAL | Page/components above plus `frontend/src/components/SourceAdminPanel.tsx`; focused tests in `SourceAdminPanel.test.tsx`, `SetupStatusPage.test.tsx`, `PublicContextPage.test.tsx`; comprehensive state transition tests remain. |
| Design shared system, responsiveness, keyboard, contrast, reduced motion, screen readers | NOT RUN | `frontend/src/styles/tokens.css`, `frontend/src/styles/global.css`, reusable `frontend/src/components`; unit tests do not establish viewport or accessibility acceptance; full visual/accessibility review not run. |
| Architecture modular monolith, repository/data boundary, PostgreSQL, private storage, DB worker, server sessions/CSRF, secret boundary | PARTIAL | `backend/app/db`, `backend/app/storage`, `backend/app/worker.py`, `backend/app/api/v1`, `frontend/src/api`; relevant backend test suite passed; live deployment/provider and independent worker monitoring remain unverified. |
| Architecture no false incident on failure, idempotent retries, bounded resources, undefined metrics unavailable, no unnecessary services | PARTIAL | `backend/app/worker.py`, `backend/app/services/opencv_models.py`, `backend/app/services/evaluation_metrics.py`, `backend/app/services/storage_cleanup.py`, `compose.yaml`; `backend/tests/test_worker.py`, `test_opencv_models.py`, `test_evaluation_metrics.py`, `test_storage_cleanup.py`; production performance and recovery drills remain incomplete. |
| Threat model and negative security regression | PARTIAL | `docs/threat-model.md`; tests cover session expiry/revocation, CSRF, role rejection, upload/path checks, configured per-instance rate limits, TinyFish public URL/privacy/response bounds, private storage signing and audit immutability. Automated secret scanning, ingress Host/body limits, distributed throttling, and live Storage policy tests remain absent/unverified. |
| Architecture release, monitoring, backup/restore, rollback and demo provenance | PARTIAL | `.github/workflows/ci.yml`, `backend/uv.lock`, `frontend/package-lock.json`, `backend/app/cli/seed_demo.py`, `docs/demo-data.md`; Actions run #40 passed on older `485c84c`, current remote HEAD `420197b` has no visible check/run; deployment and restore drills remain absent. |

### Traceability follow-up

Highest-value next local work is end-to-end route/state coverage that never impersonates model output. Then complete remaining negative authorization cases, accessibility and responsive review, worker cancellation/liveness, and live service checks when credentials and disposable services are configured. Prompt 3 is complete and Prompt 4's security delta is recorded below. `IMPLEMENTATION_PLAN.md` and the authoritative contracts govern continuing implementation without inventing any unsupplied prompt wording.

### Database invariant detail

| DATABASE.md invariant | Status | Code and proving test / limitation |
|---|---|---|
| Primary keys, required fields/defaults, foreign keys, delete rules | PARTIAL | `backend/app/db/models.py`, initial Alembic migration; disposable PostgreSQL check covers FK/rollback paths; full per-FK action matrix is not directly tested. |
| Normalized unique user email and hashed unique sessions; expiry after creation | PARTIAL | `models.py`, migration; `backend/tests/test_auth.py` checks successful auth, expiry/revocation and generic errors; DB unique/regex constraints are not all individually exercised. |
| Source/job/dataset/incident/evidence/review/run state enums and outcomes | PARTIAL | `models.py`; PostgreSQL integration checks selected constraints; exhaustive invalid-state matrix is absent. |
| Unique non-null `(source_id, source_event_id)` and duplicate ingestion idempotency | PARTIAL | Partial unique index in `models.py`/migration; concurrent disposable PostgreSQL test in `backend/tests/test_postgres_integrity.py`; skipped when DB URL is absent. |
| Nonnegative sizes, durations, attempts, counts, metric sample counts; positive duration where required | PARTIAL | Check constraints in `models.py`; only selected constraint failures are exercised by PostgreSQL integration; add full negative-value parameter matrix. |
| Incident/event and evidence clip time intervals | PARTIAL | `ck_incidents_event_interval`, `ck_evidence_offset_interval`; invalid incident interval tested in PostgreSQL integration; evidence interval boundary test remains. |
| JSON object/array shape for source config, job output, assessments, asset labels, metrics, context | PARTIAL | JSON shape checks in `models.py`/migration; no exhaustive malformed-shape integration test. |
| Unique dataset name/version, dataset asset key, run/job, metric key/scope, storage backend/key | PARTIAL | Unique constraints in `models.py`/migration; duplicate source ingestion is covered, other unique rules are not individually covered in CI's default SQLite/mock suite. |
| Correct job target for each type; evaluation dataset/run consistency | PARTIAL | Job target DB check and application checks; PostgreSQL integration covers schema-level constraints only; cross-entity consistency negative tests remain. |
| Evaluation assets eligible only with complete labels and duration; ground truth intervals in asset bounds | PARTIAL | Checks/application validation in `models.py` and evaluation services; full edge-case matrix not directly tested. |
| Prediction immutability, review separation, external context separation, append-only audit | PARTIAL | Separate model tables and audit trigger migration; `backend/tests/test_postgres_integrity.py` tests audit update/delete denial; disposable database required. |

### DESIGN.md acceptance criteria

| Criterion | Status | Evidence / remaining proof |
|---|---|---|
| Shared shell, typography, spacing, color tokens; evidence-first presentation | PARTIAL | `frontend/src/components/AppShell.tsx`, `frontend/src/components/AppShell.test.tsx`, `frontend/src/styles/tokens.css`, `global.css`; tablet/mobile header screenshots were checked after the responsive fix, but page-wide visual review remains incomplete. |
| Scannable incident table with specified filters | PARTIAL | `frontend/src/pages/IncidentsPage.tsx` provides date, source, category, review-status, sort, page-size, and previous/next controls; `frontend/src/pages/IncidentsPage.test.tsx` verifies request encoding, invalid date order, and page transitions. Full keyboard and visual review remains incomplete. |
| Detail separates detector output, review and evidence; missing/uncertain explicit | PARTIAL | `frontend/src/pages/IncidentDetailPage.tsx`; component-level accessibility/state proof incomplete. |
| Reliability metrics show context and qualified availability | PARTIAL | `frontend/src/pages/ReliabilityPage.tsx`, backend reliability API; no full screenshot review. |
| Loading, empty, error, failed, unavailable, uncertain states consistent | PARTIAL | Page/components; `SourceAdminPanel.test.tsx`, `SetupStatusPage.test.tsx`, `PublicContextPage.test.tsx`; many page-state transitions remain untested. |
| Reusable buttons, fields, status, tables, dialogs | PARTIAL | Reusable components in `frontend/src/components`; no dedicated design-system component inventory/test. |
| Desktop/tablet/mobile usability | PARTIAL | `frontend/src/styles/global.css`; manual browser checks at 1024 px and 390 px verified wrapped navigation and no horizontal overflow on the protected-screen session-error state. Broader page and interaction coverage remains unverified. |
| Visible keyboard focus and all actions keyboard-operable | NOT RUN | CSS focus styles exist; no keyboard-only full journey run. |
| Color is not sole status signal | PARTIAL | Text-bearing `StatusBadge` and labels; contrast audit not run. |
| Restrained motion and reduced-motion preference | PARTIAL | CSS includes reduced-motion rules; browser verification not run. |
| No decoration obscures evidence | NOT RUN | No formal visual evidence-player review. |
| DEMO/prerecorded content identified | PARTIAL | Source UI and `docs/demo-data.md`; seeded demo journey not browser-run. |
| No fabricated metric/performance/feature claim | PASS | Reliability/evaluation use explicit unavailable status and detector block; `backend/tests/test_evaluation_metrics.py`; no production performance claim. |
| Focused public-space incident review experience | NOT RUN | Screens exist but visual review against DESIGN.md's full criteria not run. |

### ARCHITECTURE.md acceptance criteria

| Criterion | Status | Evidence / remaining proof |
|---|---|---|
| Documented API-only frontend/backend communication | PARTIAL | `frontend/src/api/client.ts`, FastAPI routers; route/API inventory exists, but several positive contract tests are missing. |
| Modular monolith; DB access isolated from HTTP handlers | PARTIAL | `backend/app/api/v1`, `backend/app/services`, `backend/app/db`; some route-level DB queries remain. |
| PostgreSQL authoritative state; prediction/reliability/review separated | PARTIAL | SQLAlchemy models/Alembic migration; PostgreSQL integration is opt-in. |
| Video/evidence outside public frontend; authorized evidence access | PARTIAL | `backend/app/storage/supabase.py`, evidence route, private bucket policy doc; live Supabase not verified. |
| Long-running processing through background job | PASS | `backend/app/worker.py`, source upload routes; worker tests cover queue paths. |
| Failure never silently becomes confirmed incident; retries do not duplicate | PARTIAL | Worker marks failure; unique incident key and PostgreSQL test; no genuine event detector and no full worker restart/storage recovery matrix. |
| Evaluation traceable to versioned inputs/rules; undefined metrics unavailable | PARTIAL | Evaluation models and matching rule in `evaluation_metrics.py`; pure metric fixtures pass, run persistence remains detector-blocked. |
| Sessions/CSRF and backend-only secrets | PARTIAL | `auth.py`, config, `.env.example`; auth tests pass; live deployment config remains unverified. |
| Migrations and automated tests in workflow | PARTIAL | Alembic, CI workflow and locked dependencies are present; local `make check` passed. No Actions run is visible for remote HEAD `420197b` in the inspected feed, and the exact-SHA combined status is empty; the PostgreSQL integration test skips without its disposable database URL. |
| Application and worker independently monitored | PARTIAL | `backend/app/main.py` separates readiness; worker is honestly `not_reported`; true worker liveness not yet measured. |
| No unnecessary infrastructure | PASS | `compose.yaml` has PostgreSQL, API and one worker; no Redis/Celery/Kafka or microservices. |
| Simulated data never represented as live/model output | PARTIAL | Explicit source labels and `seed_demo.py`; frontend/admin UI tests pass, full browser demonstration not run. |
| Model, evidence and deployment decisions documented | PARTIAL | `docs/model-artifacts.md`, `docs/implementation-decisions.md`, `docs/supabase-storage.md`; event detector and live deployment are unavailable. |

## Prompt 1 — GitHub Actions and CI diagnosis

Current branch is `main`. GitHub's latest commit search returned remote HEAD `420197b2cb491108d63053a858ab621beae44371` ([commit](https://github.com/utkrishtchopra2008-cpu/safecity/commit/420197b2cb491108d63053a858ab621beae44371)). Exact-SHA combined status returned an empty status list. The integration's workflow-run lookup filters to PR-triggered runs; the public [Actions page](https://github.com/utkrishtchopra2008-cpu/safecity/actions) listed run #40 at `485c84c7b437adf23ff736bb870c5de99859f823` as its latest run, successful; it predates current remote HEAD and does not prove its checks. No current-HEAD run was visible in that feed. **Current HEAD Actions result: NOT VERIFIED.**

Historical failure investigation: [run #16](https://github.com/utkrishtchopra2008-cpu/safecity/actions/runs/39839223489) on `ae285428e1b4c23e46fd3e1d57619093618bd89a` had frontend checks pass; backend lint and format pass; backend mypy failed because `app/api/v1/sources.py` imported missing `app.media.uploads` (`import-not-found`); backend tests were consequently skipped. The next [run #17](https://github.com/utkrishtchopra2008-cpu/safecity/actions/runs/39839691034) on `a7c8be49c10f53c7b140fed1128694f3d001f1c2` passed both backend and frontend jobs. Its commit adds `backend/app/media/uploads.py` (118 lines) and the job log records typecheck and test success (70 passed, 3 skipped). This later commit is the evidenced fix for #16. Runs #18–#40 are shown as successful on the public page; the page did not expose their logs in this audit. Run #40's successful conclusion is confirmed on that page only, not inferred from older success.

The connected GitHub integration did not expose a list-all-push-workflow-runs API. Current status therefore combines latest-commit search, exact-SHA status lookup, exact-SHA PR-run lookup, and the public Actions feed. No current run URL was present in inspected results; latest visible run URL is https://github.com/utkrishtchopra2008-cpu/safecity/actions/runs/39868184903 (run #40).

## Feature-path findings and status semantics

| Area | Finding status | Current evidence and limitation |
|---|---|---|
| Session, roles, CSRF, CORS | PARTIAL | `backend/app/api/v1/auth.py`, `backend/app/main.py`, `backend/app/core/config.py`; `backend/tests/test_auth.py`, `test_config.py`. Server cookie sessions, revocation/expiry, CSRF and configured origin checks are present. Roles are institution-wide; per-source/tenant membership boundaries are not modeled. Rate limiting is per process. |
| Typed API, route inventory, stable error contract | PARTIAL | Routes are registered in `backend/app/api/v1/router.py`; Pydantic models in `schemas.py`; common error behavior in `backend/app/core/errors.py`; route modules listed below. Auth and selected status/review tests exist; many endpoint success, validation, authorization and error-envelope combinations remain unproved. |
| Streaming uploads and media checks | PARTIAL | `backend/app/media/uploads.py` streams bounded chunks to a private temporary file, hashes, checks extension/MIME/signature, OpenCV metadata, duration, dimensions and first-frame decode; `backend/tests/test_video_uploads.py`. Request-level ingress/proxy body caps, adversarial codec matrix and wall-clock/resource tests are not verified. |
| OpenCV timeline, sample mapping, quality and model provenance | PARTIAL | `backend/app/worker.py`, `backend/app/services/opencv_models.py`, `docs/model-artifacts.md`; `backend/tests/test_opencv_models.py`, `test_worker.py`. Sampled quality and optional object/face-region observations exist, not event detection. Two artifact-backed checks skipped because local checksum-verified artifacts are unavailable; no bounded runtime benchmark is claimed. |
| Job lifecycle: atomicity, idempotency, retry, cancellation, orphan handling | PARTIAL | `backend/app/worker.py`, `backend/app/services/storage_cleanup.py`, `backend/app/cli/cleanup_orphan_storage.py`; worker/cleanup tests and earlier disposable PostgreSQL run. Bounded attempts/lease recovery and orphan reference rechecks are covered. Cancellation has no route/state contract; live storage cleanup, process-crash recovery and all external side-effect windows are unverified. |
| DB transactions, invariants, migration rollback | PASS for tested invariants; PARTIAL overall | `backend/app/db/models.py`, `backend/migrations/versions/0001_initial_schema.py`, `backend/tests/test_postgres_integrity.py`. The full Prompt 2 suite without a database URL skipped the opt-in test; that test was then run directly and passed against a fresh disposable PostgreSQL database, and passed again after downgrade/re-upgrade. Offline SQL generation and model/migration table-set comparison passed. Hosted Supabase migration/policy and exhaustive invariant coverage remain NOT RUN. |
| Private storage and resource ownership | PARTIAL | `backend/app/storage/supabase.py`, `backend/app/api/v1/evidence.py`, `docs/supabase-storage.md`; `backend/tests/test_supabase_storage.py`, `test_auth.py`. Adapter and signed URL bounds are mock-tested; real bucket privacy/RLS and source membership checks are unverified. |
| Secrets, deployment, observability, retention | PARTIAL | `.env.example`, `backend/app/core/config.py`, `backend/app/main.py`, `backend/app/services/audit.py`, `docs/threat-model.md`. Production validation and request IDs/redacted failures exist; no live deployment, worker heartbeat monitor, backup/restore drill, confirmed retention period, or destructive retention operation is evidenced. |
| Evaluation definitions and claims | PARTIAL | `backend/app/services/evaluation_metrics.py`, `backend/tests/test_evaluation_metrics.py`, evaluation API/UI. Hand-calculated helper definitions have tests; no approved detector+dataset, persisted validated run, or real reliability metric is available. UI/API must preserve unavailable states. |
| TinyFish boundary, timeouts, failure, freshness and provenance | PARTIAL | `backend/app/services/tinyfish.py`, `context_jobs.py`; `backend/tests/test_tinyfish.py`, `test_context_jobs.py`. Mock tests cover public URL/data boundaries, response caps, attribution, unknown/stale publication times and graceful failure. Live credentials/provider, cross-process search cooldown and live freshness behavior are unverified. Core workflow independence is mock-covered. |
| Required pages and states | PARTIAL | Router maps login, dashboard, incidents/detail, reliability, evaluations, system/source status, setup, public search/source context. Tests exist for API client, dashboard, incident filter, source admin, shell, setup and public context. There are no complete page-state matrices; some typed pages lack focused component tests. |
| Responsive and accessibility behavior | PARTIAL | Shared CSS tokens/global styles and shell skip-link/nav test; prior visual spot-check at 1024 and 390 px is recorded. Full keyboard-only journey, WCAG contrast, screen reader announcements, reduced-motion browser check and all-page narrow viewport review are NOT RUN. |
| CI reproducibility | PARTIAL | `.github/workflows/ci.yml`, `Makefile`, `backend/pyproject.toml`, lockfiles. Exact commands are documented below. Prompt 0 local `make check` passed with explicit test skips; current remote Actions is not verified. Docker startup/deployment is not part of CI. |

## Requirement-to-file/test traceability matrix

The detailed matrices above and below are grouped only where one source requirement family has shared proof. Each row names implementation evidence and a proving test; absent direct proof is called out. Status reflects available evidence, not assumed completeness.

| Requirement family | Status | Implementation evidence | Proving test / outstanding proof |
|---|---|---|---|
| PRD product intent/goals/non-goals and journeys A–F (`PRD.md` §§1–5) | PARTIAL | Auth, incident review, reliability/evaluation display, source intake, public context; safety limits in `AGENTS.md` and `docs/implementation-decisions.md` | Journey coverage across frontend/API is incomplete; existing route, worker, and UI tests named in PRD rows above. No object observation may be represented as an event. |
| PRD FR-001–044 and AT-01–15 (`PRD.md` §§6,16) | PARTIAL | FR groups and AT groups in preceding detailed trace | Current default suite proves selected isolated behaviors; missing detector/data, route combinations, live storage, and E2E remain blocked or not run. |
| API authentication, users, dashboard, incident list/detail/review, evidence | PARTIAL | `backend/app/api/v1/{auth,dashboard,incidents,evidence}.py`, `schemas.py`; frontend typed client and corresponding pages | `backend/tests/test_auth.py`, `frontend/src/api/client.test.ts`, dashboard/incident component tests. List/detail response, ownership, signed-content success and error-envelope coverage is incomplete. |
| API sources, upload, process, context, job/status, reliability, evaluation, public search/fetch | PARTIAL | `backend/app/api/v1/{sources,jobs,reliability,evaluations,public_context}.py`; `backend/app/api/v1/router.py` | `test_video_uploads.py`, `test_worker.py`, `test_context_jobs.py`, `test_evaluation_metrics.py`, `test_tinyfish.py`, selected `test_auth.py`. Direct success/error/schema test for every endpoint is incomplete. |
| API schemas, pagination/filtering, common error code/status/request ID, idempotency and cancellation (`API.md` §§2–15) | PARTIAL | `backend/app/api/v1/schemas.py`, `backend/app/core/errors.py`, route modules | Client filter tests and selected standardized-error tests exist; full OpenAPI-to-API.md diff and route-by-route error contract suite are NOT RUN. Cancellation is not specified; do not silently extend `failed`. |
| DATABASE entities, FK/delete rules, state/check/unique/index constraints, JSON shape, ownership, immutability, audit, migration/seed (`DATABASE.md` §§4–14) | PARTIAL | `backend/app/db/models.py`, `0001_initial_schema.py`, audit service, demo seed | `backend/tests/test_postgres_integrity.py`, `test_seed_demo.py`; PostgreSQL test skipped by default. Earlier disposable DB run evidence in Prompt 0; full constraint matrix and hosted Supabase are not run. |
| DESIGN pages and components: login, dashboard, incident list/detail, reliability, status/source, evaluation, public context (`DESIGN.md` §§6–15) | PARTIAL | `frontend/src/app/router.tsx`, `frontend/src/pages/`, `frontend/src/components/` | Component tests exist for shell/dashboard/incidents/source-admin/setup/context/API client; pages without tests and full visual QA remain NOT RUN. |
| DESIGN loading/empty/error/unavailable/uncertain/failed/demo states | PARTIAL | Page modules, `StatusBadge`, `SourceAdminPanel`, setup/context components | `SourceAdminPanel.test.tsx`, `SetupStatusPage.test.tsx`, `PublicContextPage.test.tsx`; no complete state-to-screen matrix. |
| DESIGN keyboard, focus, contrast, semantics, screen readers, reduced motion and responsive criteria (`DESIGN.md` §§16–18) | PARTIAL | `AppShell.tsx`, `AppShell.test.tsx`, `global.css`, `tokens.css` | Shell landmark/skip-link and prior viewport spot-check; comprehensive keyboard/a11y/contrast audit is NOT RUN. |
| ARCHITECTURE modular monolith, boundaries, video pipeline/model, PostgreSQL/private storage/worker, security/observability/deployment (`ARCHITECTURE.md` §§1–22) | PARTIAL | Backend modules, Compose, storage adapter, DB worker, safety/model docs | Tests in rows above. Live deployment, monitoring, restore/rollback, resources, retention remain unverified. |
| ARCHITECTURE acceptance criteria (`ARCHITECTURE.md` §23) | PARTIAL | Acceptance rows above and subsystem implementation paths | Existing CI/local suite covers unit and typed checks, not live services, full acceptance journey or operations. |
| CI and development checks (`.github/workflows/ci.yml`, `Makefile`) | PARTIAL | `Makefile`, CI workflow, `backend/uv.lock`, `frontend/package-lock.json` | Prompt 0 `make check` PASS with 3 backend skips and 16 frontend tests; Actions #40 is green but on older SHA; current remote HEAD has no checks. |

## Prompt 2 — Persistence and storage follow-up

| Requirement | Status | Implementation evidence | Proof / limitation |
|---|---|---|---|
| SQLAlchemy model and Alembic migration cover DATABASE.md entities and constraints | PASS (local verification) | `backend/app/db/models.py`; `backend/migrations/versions/0001_initial_schema.py` | Offline upgrade/downgrade generation passed; model and migration table sets matched (16/16). A fresh PostgreSQL 16 migration, `test_postgres_integrity.py`, downgrade to base, re-upgrade, and repeat integrity test all passed on an isolated disposable database with no persistent volume. Hosted Supabase remains unverified. |
| Migration-only clean database creation; no metadata `create_all` substitute | PASS (static contract) | `backend/migrations/env.py`; `backend/migrations/versions/0001_initial_schema.py` | Revision uses explicit PostgreSQL DDL and `downgrade()` drops dependencies in reverse order. `rg` found no application/test `Base.metadata.create_all()` use. Offline SQL generation passed; database execution remains unverified here. |
| Distinct prediction, reliability, human review, evaluation, and external-context facts | PARTIAL | Separate SQLAlchemy tables and API/service modules in `backend/app/db/models.py`, `backend/app/api/v1/`, `backend/app/services/` | Structure is present; live data provenance and end-to-end product validation remain partial. |
| Bounded streaming upload, file validation, OpenCV decode and private storage adapter | PARTIAL | `backend/app/media/uploads.py`, `backend/app/storage/supabase.py`, `backend/app/api/v1/sources.py` | Upload and Supabase adapter mocks pass. Live Supabase private bucket/RLS, deployed authorization, and real storage consistency remain NOT RUN. |
| Server-generated keys validated before every storage API operation | PASS (mock-tested) | `backend/app/storage/supabase.py` | Prompt 2 added key validation in signed URL path; `backend/tests/test_supabase_storage.py::test_signed_url_rejects_traversal_keys_before_network_call` proves traversal rejection before request. |
| Evidence access requires backend authorization and short-lived signed URL | PARTIAL | `backend/app/api/v1/evidence.py`; `backend/app/storage/supabase.py` | Route and 120-second URL implementation exist, but live signed-link behavior and actual private bucket policy are NOT RUN. |
| Orphan inventory and cleanup safe against referenced evidence | PARTIAL | `backend/app/cli/cleanup_orphan_storage.py`, `backend/app/services/storage_cleanup.py`, `docs/supabase-storage.md` | Mock cleanup tests pass. Live inventory/deletion and crash-window consistency are NOT RUN. |
| Backend-only secrets, configured resource/auth settings, local setup | PARTIAL | `.env.example`, `backend/app/core/config.py`, `README.md`, `docs/supabase-storage.md` | Example has placeholders and frontend config is public-only. Secret scanning cannot establish external deployment configuration; live credentials intentionally absent. |
| Hosted Supabase Storage integration | BLOCKED / NOT RUN | Supabase adapter configuration and `docs/supabase-storage.md` | No Supabase URL or service-role credential is configured. Private bucket/RLS, deployed ownership checks, signed access, and live orphan cleanup remain unverified; PostgreSQL integration was run separately against an isolated local container. |

## Repository file/folder inventory

Decision is per tracked path listed below. All 128 tracked files are **KEEP**: contracts, tests, migration/model artifacts, lockfiles, workflows and assets have direct authority, execution, import, test, or documentation roles. Searches included Python imports, frontend router imports, tests, package/build scripts, config and docs references; no tracked path is proved junk or genuinely unused. No tracked `.DS_Store`, real `.env`, video/evidence media, Python cache, virtualenv, `node_modules`, `dist`, or generated output was found. No deletion was made.

| Path | Decision |
|---|---|
| `.editorconfig` | KEEP |
| `.env.example` | KEEP |
| `.github/workflows/ci.yml` | KEEP |
| `.gitignore` | KEEP |
| `.prettierignore` | KEEP |
| `.prettierrc.json` | KEEP |
| `AGENTS.md` | KEEP |
| `API.md` | KEEP |
| `ARCHITECTURE.md` | KEEP |
| `DATABASE.md` | KEEP |
| `DESIGN.md` | KEEP |
| `IMPLEMENTATION_PLAN.md` | KEEP |
| `Makefile` | KEEP |
| `PRD.md` | KEEP |
| `README.md` | KEEP |
| `backend/.dockerignore` | KEEP |
| `backend/.python-version` | KEEP |
| `backend/Dockerfile` | KEEP |
| `backend/alembic.ini` | KEEP |
| `backend/app/__init__.py` | KEEP |
| `backend/app/api/__init__.py` | KEEP |
| `backend/app/api/v1/__init__.py` | KEEP |
| `backend/app/api/v1/auth.py` | KEEP |
| `backend/app/api/v1/dashboard.py` | KEEP |
| `backend/app/api/v1/evaluations.py` | KEEP |
| `backend/app/api/v1/evidence.py` | KEEP |
| `backend/app/api/v1/incidents.py` | KEEP |
| `backend/app/api/v1/jobs.py` | KEEP |
| `backend/app/api/v1/public_context.py` | KEEP |
| `backend/app/api/v1/reliability.py` | KEEP |
| `backend/app/api/v1/router.py` | KEEP |
| `backend/app/api/v1/schemas.py` | KEEP |
| `backend/app/api/v1/sources.py` | KEEP |
| `backend/app/cli/__init__.py` | KEEP |
| `backend/app/cli/cleanup_orphan_storage.py` | KEEP |
| `backend/app/cli/configure_tinyfish.py` | KEEP |
| `backend/app/cli/download_models.py` | KEEP |
| `backend/app/cli/seed_demo.py` | KEEP |
| `backend/app/core/__init__.py` | KEEP |
| `backend/app/core/config.py` | KEEP |
| `backend/app/core/errors.py` | KEEP |
| `backend/app/core/rate_limit.py` | KEEP |
| `backend/app/db/__init__.py` | KEEP |
| `backend/app/db/base.py` | KEEP |
| `backend/app/db/models.py` | KEEP |
| `backend/app/db/session.py` | KEEP |
| `backend/app/main.py` | KEEP |
| `backend/app/media/uploads.py` | KEEP |
| `backend/app/services/__init__.py` | KEEP |
| `backend/app/services/audit.py` | KEEP |
| `backend/app/services/context_jobs.py` | KEEP |
| `backend/app/services/evaluation_metrics.py` | KEEP |
| `backend/app/services/incidents.py` | KEEP |
| `backend/app/services/opencv_models.py` | KEEP |
| `backend/app/services/storage_cleanup.py` | KEEP |
| `backend/app/services/tinyfish.py` | KEEP |
| `backend/app/storage/__init__.py` | KEEP |
| `backend/app/storage/supabase.py` | KEEP |
| `backend/app/worker.py` | KEEP |
| `backend/migrations/env.py` | KEEP |
| `backend/migrations/script.py.mako` | KEEP |
| `backend/migrations/versions/0001_initial_schema.py` | KEEP |
| `backend/pyproject.toml` | KEEP |
| `backend/tests/test_auth.py` | KEEP |
| `backend/tests/test_config.py` | KEEP |
| `backend/tests/test_configure_tinyfish.py` | KEEP |
| `backend/tests/test_context_jobs.py` | KEEP |
| `backend/tests/test_evaluation_metrics.py` | KEEP |
| `backend/tests/test_health.py` | KEEP |
| `backend/tests/test_opencv_models.py` | KEEP |
| `backend/tests/test_postgres_integrity.py` | KEEP |
| `backend/tests/test_rate_limit.py` | KEEP |
| `backend/tests/test_seed_demo.py` | KEEP |
| `backend/tests/test_storage_cleanup.py` | KEEP |
| `backend/tests/test_supabase_storage.py` | KEEP |
| `backend/tests/test_tinyfish.py` | KEEP |
| `backend/tests/test_video_uploads.py` | KEEP |
| `backend/tests/test_worker.py` | KEEP |
| `backend/uv.lock` | KEEP |
| `compose.yaml` | KEEP |
| `docs/FINAL_VERIFICATION.md` | KEEP |
| `docs/demo-data.md` | KEEP |
| `docs/implementation-audit.md` | KEEP |
| `docs/implementation-decisions.md` | KEEP |
| `docs/implementation-progress.md` | KEEP |
| `docs/model-artifacts.md` | KEEP |
| `docs/supabase-storage.md` | KEEP |
| `docs/threat-model.md` | KEEP |
| `frontend/eslint.config.js` | KEEP |
| `frontend/index.html` | KEEP |
| `frontend/package-lock.json` | KEEP |
| `frontend/package.json` | KEEP |
| `frontend/public/favicon.svg` | KEEP |
| `frontend/src/api/client.test.ts` | KEEP |
| `frontend/src/api/client.ts` | KEEP |
| `frontend/src/app/router.tsx` | KEEP |
| `frontend/src/components/AppShell.test.tsx` | KEEP |
| `frontend/src/components/AppShell.tsx` | KEEP |
| `frontend/src/components/PageHeader.tsx` | KEEP |
| `frontend/src/components/SourceAdminPanel.test.tsx` | KEEP |
| `frontend/src/components/SourceAdminPanel.tsx` | KEEP |
| `frontend/src/components/StatusBadge.tsx` | KEEP |
| `frontend/src/components/Surface.tsx` | KEEP |
| `frontend/src/main.tsx` | KEEP |
| `frontend/src/pages/DashboardPage.test.tsx` | KEEP |
| `frontend/src/pages/DashboardPage.tsx` | KEEP |
| `frontend/src/pages/EvaluationsPage.tsx` | KEEP |
| `frontend/src/pages/IncidentDetailPage.tsx` | KEEP |
| `frontend/src/pages/IncidentsPage.test.tsx` | KEEP |
| `frontend/src/pages/IncidentsPage.tsx` | KEEP |
| `frontend/src/pages/LoginPage.tsx` | KEEP |
| `frontend/src/pages/NotFoundPage.tsx` | KEEP |
| `frontend/src/pages/PublicContextPage.test.tsx` | KEEP |
| `frontend/src/pages/PublicContextPage.tsx` | KEEP |
| `frontend/src/pages/ReliabilityPage.tsx` | KEEP |
| `frontend/src/pages/SetupStatusPage.test.tsx` | KEEP |
| `frontend/src/pages/SetupStatusPage.tsx` | KEEP |
| `frontend/src/pages/SourceContextPage.tsx` | KEEP |
| `frontend/src/pages/SystemStatusPage.tsx` | KEEP |
| `frontend/src/styles/global.css` | KEEP |
| `frontend/src/styles/tokens.css` | KEEP |
| `frontend/src/test/setup.ts` | KEEP |
| `frontend/src/vite-env.d.ts` | KEEP |
| `frontend/tsconfig.app.json` | KEEP |
| `frontend/tsconfig.json` | KEEP |
| `frontend/tsconfig.node.json` | KEEP |
| `frontend/vite.config.ts` | KEEP |
| `frontend/vitest.config.ts` | KEEP |

Untracked/ignored inventory from `git status --short --ignored`: `backend/.mypy_cache/`, `backend/.pytest_cache/`, `backend/.ruff_cache/`, backend/app and backend/tests `__pycache__/` folders, `backend/.venv/`, `frontend/node_modules/`, and `frontend/dist/` are ignored local generated/dependency outputs. Decision: **REMOVE—PROVEN JUNK** for eventual workspace cleanup, but none were deleted during this audit. No untracked non-ignored files were present. No `.DS_Store`, local `.env`, local video/evidence files, or generated files are tracked. Directories represented by the 128 per-file rows inherit **KEEP**; no whole source/spec/test directory is a cleanup candidate.

## Precise implementation anchors

| Finding | Source location |
|---|---|
| API router registration | `backend/app/api/v1/router.py:16-24`; app mounting and middleware/error handlers `backend/app/main.py:35-157` |
| Sessions, CSRF, role checks and auth endpoints | `backend/app/api/v1/auth.py:130-220`, `:316-343` |
| Incident list/detail/reviews | `backend/app/api/v1/incidents.py:32-169` |
| Upload and source processing endpoints | `backend/app/api/v1/sources.py:124-171`, `:221-361`, `:466-471` |
| Streaming upload size, signatures, OpenCV validation | `backend/app/media/uploads.py:18-118` |
| Evidence access | `backend/app/api/v1/evidence.py:42-91`; storage signer `backend/app/storage/supabase.py` |
| Worker claim, quality sample, completion/retry and polling | `backend/app/worker.py:44-358` |
| PostgreSQL models and constraints | `backend/app/db/models.py:45-589`; initial migration/rollback `backend/migrations/versions/0001_initial_schema.py:15-211` |
| OpenCV model verification/observations | `backend/app/services/opencv_models.py:117-338`; provenance `docs/model-artifacts.md` |
| TinyFish provider boundaries | `backend/app/services/tinyfish.py:128-283`; tests `backend/tests/test_tinyfish.py` |
| Frontend routes | `frontend/src/app/router.tsx:16-34`; page files listed in traceability rows |
| Required check definitions | `Makefile:24-54`, `.github/workflows/ci.yml:12-72` |

## Exact commands and observed runtime

The repository aggregate target is `make check` (`Makefile:54`). It runs these Make targets in order: `make lint-backend`, `make format-backend-check`, `make typecheck-backend`, `make test-backend`, `make lint-frontend`, `make format-frontend`, `make typecheck-frontend`, `make test-frontend`, `make build-frontend`. Under the hood, backend targets are `cd backend && uv run ruff check app tests migrations`, `uv run ruff format --check app tests migrations`, `uv run mypy app`, `uv run pytest`; frontend targets are `npm --prefix frontend run lint`, `format:check`, `typecheck`, `test:run`, and `build`. CI additionally installs through `uv sync --locked --group dev` and `npm ci --no-audit --no-fund` (`.github/workflows/ci.yml:23-72`).

Observed in the current shell: Node `v24.22.0`, Python `3.14.7`, Docker `29.8.2`, Docker Compose `v5.6.0`; `uv` is **not available on this shell PATH**. Project constraints are Node `>=22.12.0 <23` (`frontend/package.json:6-8`) and Python `>=3.12,<3.13` (`backend/pyproject.toml:1-5`). Prompt 0's aggregate `make check` result was obtained in a separately selected compatible runtime (Node 22.16.0, Python 3.12.14) with committed lockfiles, not with current host-default versions. Prompt 1 did not rerun the checks or start Compose services. Do not treat runtime presence as Docker service verification.

## Prompt 3 — Video-processing delta

| Requirement | Status | Implementation/evidence | Verification |
|---|---|---|---|
| Upload byte caps, signature/MIME/extension, decoder metadata, dimensions/duration and typed media failures | PARTIAL | `backend/app/media/uploads.py` streams at 1 MiB chunks; failure codes include empty, too large, unsupported codec, invalid signature/metadata, and corrupt/truncated first frame. OpenCV validates stream metadata and decodes an initial frame. Full-container decode is not guaranteed at intake; later bounded sample decode failures become quality uncertainty. | `backend/tests/test_video_uploads.py` (stream cap, empty/signature/decoder and metadata failures; generated AVI path). |
| Uniform bounded frame sampling and honest source timestamps | PASS | `backend/app/services/video_sampling.py`, `backend/app/worker.py`, `backend/app/services/opencv_models.py`; sampling by frame index, timestamps only from decoder `CAP_PROP_POS_MSEC`, strictly increasing and otherwise explicitly unavailable. | `backend/tests/test_video_sampling.py`, `backend/tests/test_worker.py`. |
| Versioned measurable quality and optional configurable thresholds | PASS | `backend/app/services/video_types.py`, `backend/app/worker.py`, `backend/app/core/config.py`, `.env.example`; resolution, luma, Laplacian variance, decode failures, nominal FPS and timestamp availability each carry method/version/config/status/reason; no default threshold or event conclusion. | `backend/tests/test_worker.py` verifies known luma and configured dark/blur uncertainty; config checks in `backend/tests/test_config.py`. |
| Verified object detector provenance and typed bounded outputs | PARTIAL | `backend/app/services/opencv_models.py`, `backend/app/services/video_types.py`, `docs/model-artifacts.md`; pinned YOLOX-S INT8BQ/YuNet SHA/license/runtime, CPU DNN, typed normalized object boxes and score semantics, max 31 uniform frames/500 records; faces remain count-only; event detector remains not implemented. Model weights are absent locally, so artifact-backed runtime tests skip and configured real inference is not demonstrated. | `backend/tests/test_opencv_models.py` validates score/box/output/checksum/missing-artifact behavior; two exact-model tests SKIPPED due absent files. |
| Bounded result schema and privacy-safe job serialization | PASS | `backend/app/api/v1/jobs.py` validates nested records against typed schemas, caps results and filters paths/arbitrary metadata; `API.md` records the updated object box contract and keeps face output count-only. | `backend/tests/test_auth.py` verifies valid nested records survive and malformed/private metadata is filtered. |
| Required operator quality uncertainty state | PASS | `frontend/src/components/SourceAdminPanel.tsx` labels uncertain quality and its reasons, or explains that configured thresholds are absent; measurements remain explicitly observations. | `frontend/src/components/SourceAdminPanel.test.tsx` checks the uncertain warning and reason text. |
| Cancellation, retry and temporary cleanup | PARTIAL | `backend/app/worker.py` removes per-job temporary files in `finally`, closes storage, and removes only old regular worker files on restart. Durable cancellation is not an API/database state and remains undefined. | `backend/tests/test_worker.py` exercises Python task cancellation cleanup and lease retry; no user cancellation endpoint/state is implemented. |

The available OpenCV upload/quality path is exercised with a generated AVI, and the broader mocks cover bounds, invalid metadata, missing artifacts, uncertainty, API serialization, cancellation cleanup, duplicate claim behavior, and lease retry. No model-backed inference, live Supabase retrieval, full adversarial codec corpus, wall-clock process isolation, or production throughput claim is verified. `MODEL_UNAVAILABLE` is returned when pinned artifact files are absent; `MODEL_CHECKSUM_INVALID` is returned for bytes that do not match the pinned SHA-256. No incident/event detector exists, so objects and quality remain observations and event status remains explicitly unconfigured.

## Prompt 4 — Authentication and security hardening delta

| Requirement | Status | Evidence | Verification |
|---|---|---|---|
| Single server-side session model, token hashing, expiry/revocation, cookie protections | PASS | `backend/app/api/v1/auth.py`, `backend/app/db/models.py`; no parallel JWT/identity scheme. Cookie flags derive from configured policy; session rows hold token hashes. | `backend/tests/test_auth.py`: token hash storage, logout revocation, absolute/idle expiry, revoked and inactive user cases. |
| CSRF and browser-origin validation | PASS | HMAC CSRF token and origin validation in `backend/app/api/v1/auth.py`; configured allowlist in `backend/app/core/config.py`. | `backend/tests/test_auth.py`: missing token, logout, untrusted login Origin. |
| Role/resource API authorization | PARTIAL | Route role gates and job/evaluation ownership checks exist; single-institution schema has no source membership/tenant ownership contract. Technical admins are explicitly denied evidence access by current API policy. | `backend/tests/test_auth.py` verifies unauthenticated routes, role denial and generic evidence-route permission errors; comprehensive per-role/per-resource matrix remains incomplete. |
| Security headers and API response caching | PASS | `backend/app/main.py` sets no-store across `/api/v1/`, nosniff, frame denial, same-origin referrer, restrictive Permissions-Policy, and conditional HSTS. | `backend/tests/test_auth.py::test_api_security_headers_and_no_store_are_set`; `test_secure_cookie_configuration_emits_secure_cookie_and_hsts`. |
| Request/body limits, Host validation, deployment throttling | PARTIAL | Upload staging caps bytes and process-local route limits exist; JSON bounds come from endpoint schemas. | No global ASGI body cap or API Host allowlist; multipart can spool before staging. Require ingress body cap and Host validation. Current throttles are not shared across replicas. |
| Provider, upload/parser, secrets, signed URLs, audit/deletion threats | PARTIAL | Controls and negative coverage are summarized in `docs/threat-model.md`; source tests include upload signature/path checks, TinyFish URL/redirect/provider bounds, storage signing, and append-only audit. | `backend/tests/test_video_uploads.py`, `test_tinyfish.py`, `test_supabase_storage.py`, `test_postgres_integrity.py`; secret scanning and live Supabase policy checks are not configured. |

### Prompt 4 verification

- `backend/.venv/bin/ruff check app tests migrations` — **PASS**.
- `backend/.venv/bin/ruff format --check app tests migrations` — **PASS** (59 files formatted).
- `backend/.venv/bin/mypy app` — **PASS** (42 source files).
- `backend/.venv/bin/pytest tests/test_auth.py -q` — **PASS** (29 passed; one Starlette/httpx deprecation warning).
- Full declared backend and frontend checks were run directly because `uv` is unavailable for `make check`: backend Ruff lint/format, mypy and pytest all **PASS** (118 passed, 3 skipped); frontend lint, Prettier, TypeScript, Vitest (16 passed) and Vite build all **PASS**. Skips require verified local model artifacts (2) and a disposable migrated PostgreSQL database (1). `make check` itself was attempted and stopped at missing `uv`; no test failure was masked.
- Live ingress configuration, cross-replica throttling, Supabase RLS, automated secret scanning, and production security validation are **NOT RUN/BLOCKED**.
