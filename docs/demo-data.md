# Local DEMO data

The deterministic walkthrough fixture is optional and local-only. It creates one simulated source and one synthetic sample record so the UI can demonstrate listing, detail, and review interactions. The sample has an explicit DEMO label, no event timestamp, no evidence, no detector score, and no reliability metric. It does not represent an actual incident or model output.

Run migrations first, set `APP_ENV=development` and a development-only `DATABASE_URL`, then from `backend/` run:

```sh
uv run alembic upgrade head
uv run python -m app.cli.seed_demo --apply
```

The command requires `--apply`, refuses `APP_ENV=production` (and any environment other than `development` or `test`), and uses deterministic IDs so repeated runs do not duplicate records. It does not create demo users; configure accounts through the documented local auth/setup path. Never point this command at a shared or production database. Remove the sample only through an explicitly reviewed local database reset; the command does not delete data.
