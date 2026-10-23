# Implementation decisions

## Requirements fixed by the specifications

- PostgreSQL is authoritative; SQLAlchemy 2/Alembic own schema access and changes (`DATABASE.md`, `ARCHITECTURE.md`).
- Use the `API.md` server-managed cookie session as the sole application auth model. The three roles and permission matrix are fixed in `API.md` §3.4.
- Preserve separate immutable detector output, quality/reliability assessment, human review, and public context (`PRD.md`, `DATABASE.md`).
- Do not implement recognition, identity tracking, person-level risk scoring, accusation, punishment, or dispatch (`AGENTS.md`, `PRD.md` §2.2).
- Treat TinyFish as optional public-web context only. It cannot consume video/evidence or affect detection/review; missing credentials must not block core flows (`AGENTS.md`, `API.md` §8.2).
- Allow source-level public context on an uploaded clip only after the technical administrator enables it with a coarse area label; because the upload schema has no topic field, configure only the documented `public_notice` default. Context remains separate from the video and cannot consume media.
- Keep retention configurable; the PRD marks destructive retention behavior approval-dependent. No automatic deletion policy is inferred.

## Safe implementation choices resolved by the architecture

- Keep the modular monolith and a PostgreSQL-backed worker; do not add Redis/Celery or a second auth provider.
- Keep local development storage outside the public tree and place Supabase Storage behind a server adapter when selected. Server-generated keys and backend authorization remain required even with a privileged service credential.
- Keep event classification unavailable: the selected models detect COCO object classes and face regions only. They do not implement an incident/event taxonomy; no incident prediction or evaluation is manufactured from these outputs.
- The worker performs bounded OpenCV quality sampling for uploaded clips and bounded TinyFish Search/Fetch for explicitly enabled sources. Uploaded clips use only the documented `public_notice` context topic because the upload contract has no topic field. Context never receives video/evidence and creates no incident predictions; evaluation jobs fail safely until a verified detector/evaluation handler exists.
- Use the existing framework, package managers and pinned frontend dependencies. Do not upgrade major versions or add an unsupported provider/model.
- Treat unavailable/null metric values as unavailable, never as zero; persist provenance needed to reproduce actual calculations.
- Keep job cancellation unavailable until its contract is defined. Prompt 2 asks for cancellation, but `API.md` §4.7 defines only job-status reads and `DATABASE.md` §4.5 restricts job states to `pending`, `running`, `completed`, and `failed`; neither defines cancellation authorization, transition semantics, or behavior for work already executing. Do not overload `failed` or add an endpoint/state silently. A contract amendment should specify cancellation before implementation.
- Prompt 1's Actions review confirms historical run #16 failed on missing import `app.media.uploads` during mypy and run #17 passed after commit `a7c8be4` added that module. Current remote `main` is `420197b`; it has empty combined status; PR-only workflow-run lookup cannot answer push events, while the Actions feed shows no current-HEAD run. Do not call CI green for that commit based on older run #40.
- Apply the API.md single-instance starting limits to source registration/upload/processing and evaluation creation using bounded in-process sliding windows. They are intentionally not represented as distributed enforcement; multi-instance deployment needs a trusted proxy/shared limiter.
- The implemented evaluation metric helper uses exact category plus positive interval overlap, maximum-cardinality one-to-one matching, and stable tie-breaking. It is bounded to 1,000 combined events. This is recorded as a versioned implementation rule; the calculation helper is not yet connected to a worker or persisted evaluation run.

## Unresolved/blocked items

- Prompt 2 was supplied and completed for persistence/storage. Prompts 3 and 4 have not yet been supplied in this conversation. Job cancellation is not a Prompt 2 requirement; it remains unimplemented because `API.md` and `DATABASE.md` do not define its authorization or state-transition contract. Do not infer cancellation semantics from another task.
- Backend checks run with the committed `backend/uv.lock`; the optional PostgreSQL test skips when no disposable database URL is configured.
- A disposable PostgreSQL migration/integrity run was completed earlier in this work session. No Supabase project credentials are configured, so live RLS and private Storage checks remain unavailable.
- The API endpoint catalogue is inventoried in `docs/implementation-audit.md`; several responses/role paths still lack positive contract tests. Resource authorization follows the single-institution contract and has no source-membership/tenant schema. RLS policies in `docs/supabase-storage.md` still need application in a configured project.
- A pinned OpenCV Zoo YOLOX-S INT8BQ object model (Apache-2.0, SHA-256 verified) and YuNet face-region model (MIT, SHA-256 verified) are now implemented as optional CPU-only observation detectors. See `docs/model-artifacts.md`. Model files remain outside Git and fail closed on checksum mismatch. Their COCO/WIDER-Face behavior does not provide event classification, face recognition, or production performance claims.
- No approved incident/event detector or licensed evaluation dataset was found. Real event inference, incident generation from uploads, and detector-backed evaluation remain blocked; no fabricated event output will be added.
- No TinyFish secret is configured. Provider behavior can only be implemented and verified with mocks until an operator configures a backend secret.
- The README demo video is a user-provided presentation link; its footage provenance and usage permission are not established by repository documentation. Treat it as presentation material only, not as authorized test, training, or evaluation data. The documented local walkthrough fixture is synthetic and clearly labelled (`docs/demo-data.md`). No real footage or external data was used in Prompt 0.
- Prompt 1's repository inventory marks all 128 tracked files KEEP; only ignored caches, virtual environment, `node_modules`, and frontend build output are proven generated local artifacts. No deletion occurred. Current remote Actions status is not verified for SHA `420197b2cb491108d63053a858ab621beae44371`.

## Audit finding on authority mismatch

The root specifications define a complete product, while this checkout now contains only selected foundation and workflow slices. `docs/implementation-audit.md` records implemented scope and remaining proof. The setup screen and API remain explicit about unavailable capabilities; the app is not a complete or production-ready product.
# Prompt 2 implementation decisions (2026-10-23)

- **Keep the existing schema revision:** reviewed SQLAlchemy models and `0001_initial_schema.py` against `DATABASE.md`; no concrete schema mismatch justified adding a migration. All 16 model tables match the migration. Clean PostgreSQL 16 upgrade, integrity tests, downgrade to base, and re-upgrade passed against a disposable database with no persistent volume.
- **Fail closed on signed object keys:** use the same relative-key/traversal validation for signed URL requests as uploads, reads, existence checks, and deletion. This is a defensive storage-boundary fix and does not alter the API or key format.
- **Live Supabase remains unverified:** the code and docs require a private bucket and deny direct anon/authenticated access; service-role requests bypass RLS, so backend role/resource authorization remains required. Do not report RLS, live signed access, or orphan cleanup as verified without a configured non-production project.
- **No hosted-service credentials:** no Supabase URL or service-role key is configured. Local PostgreSQL verification and HTTP mocks passed, but they do not establish live Supabase RLS, private bucket configuration, signed access, or cleanup behavior. Do not invent credentials or present those external checks as passed.
# Prompt 3 decisions

## Object-observation API detail

- **Conflict:** `API.md` previously limited model output to aggregate class summaries and explicitly excluded boxes. Prompt 3 now requires bounded object records with normalized coordinates, frame index, source timestamp state, model version, score semantics, and evidence reference.
- **Decision:** adopt the newer explicit Prompt 3 requirement and update `API.md` together with the implementation. Return at most 500 strictly typed object observations to the authorized job owner or technical administrator. Preserve the prior face-privacy rule: return only aggregate face-region counts, no face boxes, crops, landmarks, or image bytes. Object records remain observations only and cannot create/classify incidents.

## Quality threshold policy

- PRD/implementation decisions leave product quality thresholds unsettled. Therefore `.env.example` documents optional thresholds but defaults them to unset. Measured quality fields are still returned; aggregate status is `not_evaluated` until a threshold is configured, then `uncertain` if a configured threshold is breached. No default threshold or incident meaning is inferred.

## Cancellation semantics

- API/database contracts do not define a user-visible cancellation state or endpoint. This phase tests Python task interruption cleanup and leaves durable cancellation semantics unchanged; no new endpoint, state, or retention rule is inferred.
