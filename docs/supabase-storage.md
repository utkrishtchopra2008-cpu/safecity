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

Set `STORAGE_BACKEND=supabase`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `SUPABASE_STORAGE_BUCKET` in the backend environment. For local metadata development, run PostgreSQL and apply the versioned Alembic migrations with `DATABASE_URL`; do not use `metadata.create_all`. Keep the bucket private in every environment that handles real evidence. Until upload and authorized evidence routes are implemented and verified, do not upload real footage.

Evidence objects use server-generated relative keys. Signed URLs are scoped to one object and limited to five minutes maximum by the adapter. Uploads set the stored object cache TTL to zero because signed URL expiry and CDN cache lifetime are separate controls. The URL is sensitive and must not be logged or persisted. Retention and deletion remain explicit, approval-dependent workflows.
