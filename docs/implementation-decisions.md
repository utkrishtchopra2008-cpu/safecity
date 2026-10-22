# Implementation decisions

## Requirements fixed by the specifications

- PostgreSQL is authoritative; SQLAlchemy 2/Alembic own schema access and changes (`DATABASE.md`, `ARCHITECTURE.md`).
- Use the `API.md` server-managed cookie session as the sole application auth model. The three roles and permission matrix are fixed in `API.md` §3.4.
- Preserve separate immutable detector output, quality/reliability assessment, human review, and public context (`PRD.md`, `DATABASE.md`).
- Do not implement recognition, identity tracking, person-level risk scoring, accusation, punishment, or dispatch (`AGENTS.md`, `PRD.md` §2.2).
- Treat TinyFish as optional public-web context only. It cannot consume video/evidence or affect detection/review; missing credentials must not block core flows (`AGENTS.md`, `API.md` §8.2).
- Keep retention configurable; the PRD marks destructive retention behavior approval-dependent. No automatic deletion policy is inferred.

## Safe implementation choices resolved by the architecture

- Keep the modular monolith and a PostgreSQL-backed worker; do not add Redis/Celery or a second auth provider.
- Keep local development storage outside the public tree and place Supabase Storage behind a server adapter when selected. Server-generated keys and backend authorization remain required even with a privileged service credential.
- Keep detector mode explicitly simulated until an artifact, license, checksum, input/output contract and CPU runtime are independently verified. Simulated records must be labelled DEMO.
- The worker performs bounded OpenCV quality sampling for uploaded clips and bounded TinyFish Search/Fetch for explicitly enabled simulated sources. It creates no incident predictions; evaluation jobs fail safely until a verified detector/evaluation handler exists.
- Use the existing framework, package managers and pinned frontend dependencies. Do not upgrade major versions or add an unsupported provider/model.
- Treat unavailable/null metric values as unavailable, never as zero; persist provenance needed to reproduce actual calculations.
- The implemented evaluation metric helper uses exact category plus positive interval overlap, maximum-cardinality one-to-one matching, and stable tie-breaking. It is bounded to 1,000 combined events. This is recorded as a versioned implementation rule; the calculation helper is not yet connected to a worker or persisted evaluation run.

## Unresolved/blocked items

- The submitted prompt pack jumps from Prompt 2 to Prompt 4; Prompt 3 was not supplied. Video-processing work therefore follows only the repository authorities and the explicit Prompt 0 safety contract.
- The bundled Python 3.12 runtime was used with dependencies installed outside the repository; `uv` was unavailable. Backend lint, format, typing, and unit tests ran. The optional PostgreSQL test skips when no disposable database URL is configured.
- A disposable PostgreSQL migration/integrity run was completed earlier in this work session. No Supabase project credentials are configured, so live RLS and private Storage checks remain unavailable.
- Authentication, basic incident/review routes and limited source routes now exist. Resource authorization lacks a source-membership/tenant schema, and the complete API endpoint catalogue is still not implemented. RLS policies in `docs/supabase-storage.md` still need application in a configured project.
- No approved detector artifact/license or evaluation dataset was found. Real inference and reliability claims remain blocked; no fabricated detector output will be added.
- No TinyFish secret is configured. Provider behavior can only be implemented and verified with mocks until an operator configures a backend secret.

## Audit finding on authority mismatch

The root specifications define a complete product, while this checkout now contains only selected foundation and workflow slices. `docs/implementation-audit.md` records implemented scope and remaining proof. The setup screen and API remain explicit about unavailable capabilities; the app is not a complete or production-ready product.
