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
- Apply the API.md single-instance starting limits to source registration/upload/processing and evaluation creation using bounded in-process sliding windows. They are intentionally not represented as distributed enforcement; multi-instance deployment needs a trusted proxy/shared limiter.
- The implemented evaluation metric helper uses exact category plus positive interval overlap, maximum-cardinality one-to-one matching, and stable tie-breaking. It is bounded to 1,000 combined events. This is recorded as a versioned implementation rule; the calculation helper is not yet connected to a worker or persisted evaluation run.

## Unresolved/blocked items

- The submitted prompt pack contains Prompts 0, 1, 2, 5, 6, 7 and 8; Prompts 3 and 4 are absent. Work follows repository authorities and the explicit Prompt 0 safety contract without inferring missing prompt text.
- Backend checks run with the committed `backend/uv.lock`; the optional PostgreSQL test skips when no disposable database URL is configured.
- A disposable PostgreSQL migration/integrity run was completed earlier in this work session. No Supabase project credentials are configured, so live RLS and private Storage checks remain unavailable.
- The API endpoint catalogue is inventoried in `docs/implementation-audit.md`; several responses/role paths still lack positive contract tests. Resource authorization follows the single-institution contract and has no source-membership/tenant schema. RLS policies in `docs/supabase-storage.md` still need application in a configured project.
- A pinned OpenCV Zoo YOLOX-S INT8BQ object model (Apache-2.0, SHA-256 verified) and YuNet face-region model (MIT, SHA-256 verified) are now implemented as optional CPU-only observation detectors. See `docs/model-artifacts.md`. Model files remain outside Git and fail closed on checksum mismatch. Their COCO/WIDER-Face behavior does not provide event classification, face recognition, or production performance claims.
- No approved incident/event detector or licensed evaluation dataset was found. Real event inference, incident generation from uploads, and detector-backed evaluation remain blocked; no fabricated event output will be added.
- No TinyFish secret is configured. Provider behavior can only be implemented and verified with mocks until an operator configures a backend secret.

## Audit finding on authority mismatch

The root specifications define a complete product, while this checkout now contains only selected foundation and workflow slices. `docs/implementation-audit.md` records implemented scope and remaining proof. The setup screen and API remain explicit about unavailable capabilities; the app is not a complete or production-ready product.
