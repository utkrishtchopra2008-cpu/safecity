# SafeCity AI

SafeCity AI is a reliability-aware public-space incident intelligence platform. It helps authorized operators review candidate events using supporting evidence, uncertainty information, and measurable evaluation. Predictions are not ground truth; consequential decisions remain subject to human review.

This branch contains the initial project foundation. Feature workflows (authentication/session persistence, incident ingestion, video processing, evaluation, and TinyFish public-context retrieval) are not implemented by this scaffold yet.

## Technology

- **Frontend:** React 19, TypeScript, Vite, React Router, TanStack Query, CSS variables/CSS Modules (as needed), Lucide React, Vitest, and React Testing Library. Charting dependencies are deferred until metric charts are implemented.
- **Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, Psycopg 3, HTTPX, pytest, Ruff, and mypy.
- **Database:** PostgreSQL 16 for local development via Docker Compose.
- **External context:** TinyFish Search/Fetch is documented but disabled by default; this scaffold does not make TinyFish requests.

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

The frontend Vite server proxies `/api and `2health`  to the local backend. `VITE_API_BASE_URL` is public configuration only; do not put credentials or keys in `VITE_*` values.

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

`make check` runs the available lint, formatting, type-check, test, and frontend-build checks. PostgreSQL integration checks will be added when the database/session layer is implemented. The `/health/ready` route currently confirms that the bootstrap application and its configuration are loaded; it is **not yet a database-readiness check**.

## Repository map

```text
.
├── .github/workflows/ci.yml
├── backend/
│   ├── app/
│   │   ├── core/          # Validated configuration and shared backend concerns
│   │   ├── db/            # Declarative base; persistence is added in a later phase
│   │   ├── api/v1/        # Versioned API routing boundary
│   │   └── main.py
│   ├── migrations/        # Alembic environment; feature migrations follow with schema work
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/           # Typed API client
│   │   │   └── app/           # Router and application shell
│   │   ├── components/    # Shared foundation components
│   │   ├── pages/         # Foundation and not-found pages only
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

- The setup UI is a foundation placeholder; it does not claim to connect to live CCTV.
- No facial recognition, identity tracking, individual criminality scoring, automated accusations, or autonomous dispatch are implemented.
- TinyFish is feature-flagged in configuration and disabled by default. The key remains server-side, and no video/media or personal data may be sent to the provider.
- Actual database readiness, authentication, media processing, background jobs, incident APIs, and TinyFish calls will be introduced in the planned phases after this foundation is accepted.

## Contribution discipline

Read `AGENTS.md` and all source-of-truth specifications before implementing features. Keep changes focused, update contract documents when behavior changes, and report commands/tests that could not run rather than claiming success.
