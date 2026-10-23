# Supabase Storage setup and access policy

SafeCity stores database metadata through SQLAlchemy/Alembic and media through the backend storage adapter. The `safecity-evidence` bucket must remain private. The server's service-role credential bypasses Storage RLS, so API authentication, role checks, and evidence-to-source authorization must be performed before every upload, signed URL, stream, or deletion.

## Bucket setup

1. Create a private bucket named by `SUPABASE_STORAGE_BUCKET` (default `safecity-evidence`) in the Supabase project. Do not enable public access.
2. In the Supabase SQL editor, apply these deny-by-default policies (adapt the bucket name only if configuration differs):

```sql
create policy "safecity evidence deny direct reads"
on storage.objects as restrictive for select to anon, authenticated
using (bucket_id <> 'safecity-evidence');

create policy "safecity evidence deny direct inserts"
on storage.objects as restrictive for insert to anon, authenticated
with check (bucket_id <> 'safecity-evidence');

create policy "safecity evidence deny direct updates"
on storage.objects as restrictive for update to anon, authenticated
using (bucket_id <> 'safecity-evidence')
with check (bucket_id <> 'safecity-evidence');

create policy "safecity evidence deny direct deletes"
on storage.objects as restrictive for delete to anon, authenticated
using (bucket_id <> 'safecity-evidence');
```

These policies make direct browser access unavailable. The backend uses a service-role key only on the server; the key must never be supplied to Vite or returned from an API. Because the app's identity model is its own server-managed session and does not use Supabase Auth JWTs, `auth.uid()` policies would not identify SafeCity users. RLS is not claimed as an authorization boundary for service-role requests.

Set `STORAGE_BACKEND=supabase`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `SUPABASE_STORAGE_BUCKET` in the backend environment. For local metadata development, copy `.env.example` to an untracked `.env`, start PostgreSQL with `make db-up`, then apply the versioned Alembic migrations from `backend/` with `uv run alembic upgrade head`; do not use `metadata.create_all`. Run storage adapter tests with `uv run pytest tests/test_supabase_storage.py tests/test_storage_cleanup.py`. These use HTTP mocks and do not need a Supabase project. Keep the bucket private in every environment that handles real evidence. The upload and authorized evidence routes are implemented, but live bucket privacy/RLS and signed access have not been verified against a configured non-production project; live evidence use remains unverified.

Evidence objects use server-generated relative keys. Signed URLs are scoped to one object and limited to five minutes maximum by the adapter. Uploads set the stored object cache TTL to zero because signed URL expiry and CDN cache lifetime are separate controls. The URL is sensitive and must not be logged or persisted. Retention and deletion remain explicit, approval-dependent workflows.

## Orphan inventory and explicit cleanup

`backend/app/cli/cleanup_orphan_storage.py` inventories only generated `sources/{source UUID}/{evidence UUID}/original.{supported video extension}` keys through Supabase's Storage list API. It ignores folders without file metadata, unrecognized keys and objects with unknown creation times. It reports evidence rows whose object is missing, compares candidate objects with authoritative `evidence.storage_key` values, selects only objects older than an operator-supplied age threshold, and checks the database reference again immediately before each deletion. Missing evidence objects are reported only; the command never changes their database rows. Database transactions are closed before Storage network requests. Deletions use the Storage API, never direct edits to Supabase's `storage` schema.

Cleanup is never automatic. From `backend/`, inspect first with a threshold selected for the specific recovery operation:

```sh
uv run python -m app.cli.cleanup_orphan_storage --older-than-hours 48
```

Review every listed key, then repeat the same command with `--apply` only when the inventory is correct. The example threshold is not a retention policy; the command requires an explicit value and supports 1–8760 hours. It scans at most 5,000 files per run and fails safely above that bound. Live Supabase behavior remains unverified until exercised in a configured non-production project.

The adapter follows Supabase's documented [Storage list API](https://supabase.com/docs/reference/javascript/file-buckets-list) and [Storage deletion guidance](https://supabase.com/docs/guides/storage/management/delete-objects), which directs object deletion through the Storage API rather than SQL.

## Local development and test boundary

The default `.env.example` uses local storage mode and contains placeholders only. It is suitable for database/API development but does not enable object uploads: the upload route requires the configured Supabase backend. Never put Supabase credentials in `VITE_*` variables. Unit tests exercise the adapter and cleanup decisions with mocked HTTP; they do not prove live bucket policies, service-role permissions, signed-link behavior, or deployed ownership checks. Use a dedicated non-production Supabase project for those integration checks and record them as NOT RUN until they have actually completed.
