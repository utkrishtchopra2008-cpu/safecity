# SafeCity AI

SafeCity AI is a reliability-aware public-space incident intelligence platform. It helps authorized operators review candidate events using supporting evidence, uncertainty information, and measurable evaluation. Predictions are not ground truth; consequential decisions remain subject to human review.

This repository contains working slices of the operator workflow: server-managed authentication, incident review, technical-admin source registration and prerecorded-video upload, a PostgreSQL-backed worker, bounded OpenCV quality sampling, and optional public-context retrieval. Object and face-region observations are not event detections; a verified event detector and detector-backed evaluation are not available. See `docs/implementation-audit.md` for implemented scope, evidence, and remaining gaps.

## Technology

- **Frontend:** React 19, TypeScript, Vite, React Router, TanStack Query, CSS variables/CSS Modules (as needed), Lucide React, Vitest, and React Testing Library. Charting dependencies are deferred until metric charts are implemented.
- **Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, Psycopg 3, HTTPX, pytest, Ruff, and mypy.
- **Database:** PostgreSQL 16 for local development via Docker Compose.
- **External context:** TinyFish Search/Fetch is implemented server-side and disabled by default. Provider behavior is mock-tested; no live TinyFish request is claimed.

## Requirements

- Node.js **22.12 or newer in the 22.x line** (Vite's current compatibility requirement).
- Python **3.12.x**.
- `uv` for Python dependency management.
- Docker Desktop or Docker Engine with Compose, only if using local PostgreSQL.

## First-time setup

From the repository root:

```bash
cp .env.example .env
make setup
make db-up
```

For a containerized API plus PostgreSQL, use `docker compose up --build`; the frontend can still run with Vite in a separate terminal.

The values in `.env.example` are local development placeholders only. Never use them in production. Production must use real secrets from the deployment environment or a secret manager, HTTPS, secure cookies, and a separately reviewed configuration.

Open two terminals from the repository root:

```bash
make dev-backend
```

```bash
make dev-frontend
```

The frontend is served at `http://localhost:5173`. The backend liveness check is at `http://localhost:8000/health/live`, and development-only API docs are at `http://localhost:8000/docs`.

The frontend Vite server proxies `/api` and `/health` to the local backend. `VITE_API_BASE_URL` is public configuration only; do not put credentials or keys in `VITE_*` values.

## Useful commands

```bash
make test-backend
make lint-backend
make format-backend
make typecheck-backend
make lint-frontend
make format-frontend
make typecheck-frontend
make test-frontend
make build-frontend
make check
```

`make check` runs backend lint, formatting, type-checking and tests, followed by frontend lint, formatting, type-checking, tests and production build. PostgreSQL integration tests require `SAFECITY_TEST_DATABASE_URL` to point to a disposable migrated database and are skipped otherwise. `/health/ready` checks database readiness; it does not establish worker or storage readiness.

## Repository map

```text
.
├── .github/workflows/ci.yml
├── backend/
│   ├── app/
│   │   ├── core/          # Validated configuration and shared backend concerns
│   │   ├── db/            # SQLAlchemy models and session management
│   │   ├── api/v1/        # Versioned auth, incident, source, evidence, job, evaluation, and context routes
│   │   ├── services/      # Incident, worker, evaluation, OpenCV, and TinyFish services
│   │   ├── storage/       # Private Supabase Storage adapter
│   │   ├── cli/           # Demo seed, model setup, and storage maintenance commands
│   │   ├── main.py
│   │   └── worker.py      # PostgreSQL-backed processing worker
│   ├── migrations/        # Alembic environment and schema revision
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/           # Typed API client
│   │   ├── app/           # Router and application shell
│   │   ├── components/    # Shared components and source-admin panel
│   │   ├── pages/         # Login, dashboard, incident, reliability, evaluation, status, and context screens
│   │   └── styles/        # Design tokens and global styles
│   └── package.json
├── .env.example
├── AGENTS.md
├── API.md
├── ARCHITECTURE.md
├── DATABASE.md
├── DESIGN.md
├── IMPLEMENTATION_PLAN.md
├── PRD.md
├── Makefile
└── compose.yaml
```

## Safety and scope

- Source registration supports simulated sources and prerecorded uploads; this does not claim to connect to live CCTV.
- No facial recognition, identity tracking, individual criminality scoring, automated accusations, or autonomous dispatch are implemented.
- TinyFish is disabled by default. Its key remains server-side, and video/media, credentials, private URLs, and personal incident data must never be sent to the provider.
- The current implementation has a PostgreSQL schema and worker, server-managed sessions and CSRF checks, incident/review and evidence routes, upload validation and private-storage integration, and optional context workflows. Live Supabase and TinyFish services are not verified. No event detection is inferred from object observations or processing failures.

## Contribution discipline

Read `AGENTS.md` and all source-of-truth specifications before implementing features. Keep changes focused, update contract documents when behavior changes, and report commands/tests that could not run rather than claiming success.



## Demo Video

[Watch the SafeCity AI demo](https://github.com/user-attachments/assets/50d2e493-116f-48e6-b9dd-50ce6fd34e45)
