Warning: truncated output (original token count: 14632)
Total output lines: 1295

# SafeCity AI — API Specification

**Document:** API.md  
**Version:** 1.0  
**Status:** Proposed API contract  
**Product:** SafeCity AI  
**Source of truth:** PRD.md, ARCHITECTURE.md, and DATABASE.md

---

## 1. Purpose and Scope

This document defines how the SafeCity AI frontend, backend, background worker, database, video-processing pipeline, and storage components communicate.

The API supports the MVP's complete workflow:

1. Authenticate authorized users.
2. View operational summaries and candidate incident detections.
3. Inspect incidents, evidence, reliability assessments, and uncertainty.
4. Submit and retrieve human review outcomes.
5. Upload or register supported video sources.
6. Inspect background-processing status.
7. Run evaluations against labeled datasets.
8. Retrieve reliability metrics and evaluation results.
9. Inspect processing and source health.

The API must preserve the distinction between machine-generated detections, reliability assessments, human review outcomes, and benchmark results.

### 1.1 Scope Boundaries

The MVP uses:

- A React and TypeScript frontend.
- A FastAPI backend.
- PostgreSQL as the authoritative application database.
- A background worker for video processing and evaluation.
- Private filesystem or object storage for media.
- One configured detection pipeline or a clearly labeled simulated detector.

The MVP includes an optional-per-source, feature-flagged TinyFish Search/Fetch integration for public-web context retrieval. TinyFish is not used for video inference and must never receive surveillance media, personal data, credentials, or private URLs. The API does not include emergency-service dispatch, facial-recognition services, enterprise identity providers, or commercial video-management integrations.

### 1.2 Normative Requirements

The words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** describe implementation requirements.

Where this document proposes behavior that depends on an unapproved product decision, implementation must follow the approved decision and update this specification accordingly.

---

## 2. API Conventions

### 2.1 Base URL

All application API endpoints use the versioned base path:

/api/v1

The deployment supplies the domain and scheme. Production requests must use HTTPS.

Operational health endpoints are outside the versioned API namespace:

- /health/live
- /health/ready

### 2.2 Communication Formats

| Purpose | Format |
|---|---|
| Standard requests | JSON |
| Standard responses | JSON |
| Video uploads | multipart/form-data |
| Video and image evidence | Binary media responses |
| API errors | Problem Details-style JSON |
| API documentation | OpenAPI during development |

Requests and responses must use UTF-8 where applicable.

### 2.3 Naming Conventions

- JSON field names use snake_case.
- Endpoint paths use lowercase nouns and resource identifiers.
- Database UUIDs are represented as strings in JSON.
- Timestamps use ISO 8601 with an explicit UTC offset or Z.
- Database timestamps are stored as UTC.
- Enumerated statuses use documented lowercase values.
- Missing values are represented as null where a field is part of the response schema and unavailable.
- Empty collections are represented as empty arrays, not null.

The API must not expose internal filesystem paths, database connection details, password hashes, or session-token hashes.

### 2.4 Timestamp Example

2026-10-21T08:30:00Z

The frontend may display timestamps in the configured local timezone, but the underlying timestamps and event-time semantics must remain unambiguous.

### 2.5 Identifiers

Use UUIDs for primary resource identifiers.

The API must validate identifier formats and return a consistent not-found response for nonexistent resources. It must not rely on unpredictable IDs as a substitute for authorization.

### 2.6 HTTP Status Codes

| Status | Meaning |
|---|---|
| 200 OK | Request completed successfully |
| 201 Created | A new resource was created synchronously |
| 202 Accepted | A processing job was accepted and will complete asynchronously |
| 204 No Content | Request completed successfully without a response body |
| 400 Bad Request | Request is malformed or violates a request-level rule |
| 401 Unauthorized | Authentication is missing, invalid, or expired |
| 403 Forbidden | User lacks permission to perform the requested operation |
| 404 Not Found | Resource does not exist or is not available to the requesting user |
| 409 Conflict | Request conflicts with existing resource state or a uniqueness constraint |
| 413 Content Too Large | Uploaded data exceeds the configured size limit |
| 415 Unsupported Media Type | Request or upload format is unsupported |
| 422 Unprocessable Content | Request fields fail schema or semantic validation |
| 429 Too Many Requests | Rate limit exceeded |
| 500 Internal Server Error | Unexpected application failure |
| 503 Service Unavailable | A required dependency is temporarily unavailable |

Use these codes consistently. Do not use a successful HTTP response to imply that background video processing has succeeded.

---

## 3. Authentication and Authorization

### 3.1 Authentication Model

Use server-managed sessions, as specified in ARCHITECTURE.md.

The login flow is:

1. The user submits credentials over HTTPS.
2. The backend verifies the credentials against the stored password hash.
3. The backend generates a high-entropy session token.
4. The database stores a hash of that token in sessions.
5. The browser receives the raw session token in an appropriately configured secure cookie.
6. Subsequent requests authenticate through the cookie.
7. Logout revokes the corresponding database session.

The raw session token MUST NOT be stored in the database or exposed through API response JSON.

The implementation hashes passwords with Argon2id and generates 256-bit random session tokens. The initial configurable session defaults are an eight-hour absolute expiry and a thirty-minute idle expiry. The database stores only the SHA-256 token hash; every protected request checks expiry, revocation, idle time, and active-user state.

### 3.2 Cookie Requirements

Production session cookies must use:

- HttpOnly.
- Secure.
- An appropriate SameSite policy, normally Lax for a same-site application.
- An explicit expiration period.

The backend must reject expired, revoked, or otherwise invalid sessions. Deactivated users must not retain access through existing sessions.

### 3.3 CSRF Protection

Because authentication uses cookies, state-changing requests must be protected against cross-site request forgery.

Use a documented CSRF-token mechanism and appropriate origin validation.

If a CSRF token is returned to the frontend, it must not contain the session token or another reusable authentication secret. Validate the token on protected state-changing requests.

The implementation returns a per-session HMAC CSRF token from `GET /api/v1/auth/csrf`. The frontend sends it in `X-CSRF-Token` for state-changing requests other than login. The backend also requires the request Origin (or Referer origin) to match `PUBLIC_APP_ORIGIN` or `CSRF_ALLOWED_ORIGINS`. Production must configure a random `SESSION_CSRF_SECRET` of at least 32 characters. Authentication responses are sent with `Cache-Control: no-store`.

Authentication outcomes are written to the append-only audit table with actor (when known), action, object reference, result, timestamp, and request correlation ID. Credentials, emails, session tokens, source IP addresses, and request bodies are not stored in these audit events.

### 3.4 Roles

The API supports these roles:

- operator
- supervisor
- technical_admin

The backend must enforce role permissions and resource-level access independently of frontend navigation or component visibility.

| Operation | Operator | Supervisor | Technical administrator |
|---|---|---|---|
| View incident list and details | Yes | Yes | As authorized |
| Access evidence | If authorized | If authorized | Only when authorized and necessary |
| Submit review outcomes | Yes | Yes | No by default |
| View reliability metrics | Read-only | Yes | Yes |
| Inspect processing errors | No by default | Read-only if permitted | Yes |
| Create or configure sources | No | No by default | Yes |
| Start an evaluation | No | No by default | Yes |
| Inspect evaluation results | Read-only where permitted | Yes | Yes |
| Manage accounts | No | No by default | Only if implemented and approved |

### 3.5 Resource-Level Authorization

Every protected endpoint must:

1. Authenticate the current user.
2. Check permission for the requested operation.
3. Verify that the resource belongs to the user's permitted access scope.
4. Return only information and media the user is authorized to access.

If a resource is intentionally hidden from the requesting user, a not-found response may be used to avoid disclosing its existence.

### 3.6 Demonstration Accounts

Predefined demonstration users may be created through a controlled development seeding process.

The API must not include hardcoded production credentials or a public default administrator account.

---

## 4. Endpoint Catalogue

The tables below define the required and conditionally required endpoints.

### 4.1 Authentication

| Method | Endpoint | Purpose | Access |
|---|---|---|---|
| POST | /api/v1/auth/login | Authenticate user and create session | Public, rate-limited |
| POST | /api/v1/auth/logout | Revoke current session | Authenticated |
| GET | /api/v1/auth/me | Return current user and role | Authenticated |
| GET | /api/v1/auth/csrf | Obtain CSRF token when required by selected implementation | Session/context dependent |

#### Login request

Content type: application/json

Required fields:

- email
- password

The backend must normalize the email consistently with the database's uniqueness rules and validate the credentials.

#### Login response

Return the authenticated user's public profile and role. Set the session cookie through the HTTP response.

Do not return the raw session token, password hash, or session-token hash in JSON.

An invalid email/password combination should return a generic authentication error without revealing whether the account exists.

#### Current-user response

Return:

- User ID.
- Display name.
- Email, if appropriate for the signed-in user.
- Role.
- Account state needed by the interface.

Never return authentication secrets.

---

### 4.2 Dashboard

| Method | Endpoint | Purpose | Access |
|---|---|---|---|
| GET | /api/v1/dashboard/summary | Return operational summary and available metrics | Authenticated |

Optional query parameters:

- start_at
- end_at
- source_id

The backend must validate date ranges and resource permissions.

The response may include:

- Incident counts by review status.
- Recent incident summaries.
- Source and processing status.
- Available reliability indicators.
- Metric source and evaluation period.

Counts must be calculated over a documented period. If a metric cannot be calculated, return an explicit unavailable state instead of a fabricated value or zero.

---

### 4.3 Incidents

| Method | Endpoint | Purpose | Access |
|---|---|---|---|
| GET | /api/v1/incidents | List and filter incidents | Authenticated |
| GET | /api/v1/incidents/{incident_id} | Retrieve incident detail | Authenticated |

#### List query parameters

| Parameter | Type | Purpose |
|---|---|---|
| start_at | Timestamp | Include incidents at or after the specified event time |
| end_at | Timestamp | Include incidents at or before the specified event time |
| source_id | UUID | Filter by source |
| detection_category | String | Filter by normalized category |
| review_status | String | Filter by unreviewed or reviewed |
| sort_by | String | Approved sorting field |
| sort_order | String | asc or desc |
| page | Integer | One-based page number |
| page_size | Integer | Records per page, bounded by server configuration |

Only documented sort fields are allowed. The backend must not insert arbitrary user-supplied sorting values into SQL.

#### Incident list response

Each item should include the fields required for scanning the incident list:

- id
- source_id
- event_start_at
- event_end_at
- received_at
- detection_category
- detector_name
- detector_version
- detector_score, when available
- score_semantics, when available
- review_status
- Latest available reliability summary, if one exists

A latest assessment summary must not be fabricated if no assessment exists.

#### Incident detail response

Return:

- Incident identifiers and timestamps.
- Source metadata the user is permitted to see.
- Original detector category, label, version, and score semantics.
- Current review status.
- Evidence metadata and authorized references.
- Reliability assessments.
- Review history, if supported by the deployed implementation.
- Processing status when relevant.

The response must distinguish the original prediction, the reliability assessment, and the human review outcome. It must not represent any one of them as another.

---

### 4.4 Reviews

| Method | Endpoint | Purpose | Access |
|---|---|---|---|
| POST | /api/v1/incidents/{incident_id}/reviews | Save human review outcome | Operator or supervisor |
| GET | /api/v1/incidents/{incident_id}/reviews | Retrieve review history, when exposed by the implementation | Authorized users |

The POST endpoint is required for the MVP. Review history retrieval may be limited to the current review if historical revisions are not yet implemented.

#### Review request

Required field:

- outcome

Allowed values:

- confirmed
- false_alert
- inconclusive

Optional field:

- review_note, subject to the database's maximum length.

The backend derives reviewer_id from the authenticated session. It must never accept a client-supplied reviewer ID as authoritative identity.

#### Review behavior

The backend must:

1. Validate the incident ID.
2. Authenticate the reviewer.
3. Verify that the user's role permits reviewing.
4. Validate the outcome and note.
5. Persist the review record.
6. Update the incident's current review status.
7. Commit both database changes in one transaction.
8. Return the saved review and current review status.

The review operation must not overwrite the detector's original category, label, score, or version.

#### Review response

Return:

- id
- incident_id
- reviewer_id
- outcome
- review_note, if present
- reviewed_at
- Current incident review_status

If a repeated submission could create an unwanted duplicate, the backend must handle the retry safely, using an idempotency mechanism or an appropriate conflict rule.

---

### 4.5 Evidence

| Method | Endpoint | Purpose | Access |
|---|---|---|---|
| GET | /api/v1/evidence/{evidence_id} | Retrieve evidence metadata | Authenticated and authorized |
| GET | /api/v1/evidence/{evidence_id}/content | Stream video or image content | Authenticated and authorized |

#### Evidence metadata response

May include:

- Evidence ID.
- Source ID.
- Evidence type.
- Validated media type.
- Byte size, if available.
- Relevant clip offsets.
- Availability and processing status.
- Creation timestamp.
- Integrity checksum, if exposed to the authorized user and useful.

Do not return absolute filesystem paths, private object-store credentials, or unrestricted storage keys.

#### Evidence content behavior

- Authorize every request.
- Return the correct media content type.
- Support byte-range requests where necessary for video seeking.
- Return an appropriate error if the object is unavailable.
- Avoid loading unnecessarily large video assets entirely into application memory.
- Preserve the user's ability to inspect other incident metadata if media loading fails.

When evidence is stored in private object storage in a future deployment, a short-lived signed URL may be used only after backend authorization. Public, permanent media URLs are not permitted by default.

---

### 4.6 Sources and Video Ingestion

The MVP supports an uploaded clip, a simulated source, or both, according to the approved deployment decision.

| Method | Endpoint | Purpose | Access |
|---|---|---|---|
| GET | /api/v1/sources | List configured sources | Authenticated |
| GET | /api/v1/sources/{source_id} | Retrieve source details | Authenticated and authorized |
| POST | /api/v1/sources | Register an approved simulated source | Technical administrator |
| POST | /api/v1/sources/upload | Upload a prerecorded clip and create source/evidence/job records | Technical administrator |
| POST | /api/v1/sources/{source_id}/process | Request video processing or an approved reprocessing operation | Technical administrator |
| GET | /api/v1/sources/{source_id}/context | List public context items linked to the source, with freshness metadata | Authenticated and authorized |
| POST | /api/v1/sources/{source_id}/context-refresh | Enqueue a bounded TinyFish public-context refresh | Supervisor or technical administrator |

Upload and processing endpoints should be implemented only for the source modes selected for the MVP.

#### Simulated source registration

Content type: application/json

Fields:

- name
- source_type, fixed to simulated
- Optional non-sensitive configuration supported by the chosen simulator
- Optional `context_area_label`: coarse, approved public area used to search for relevant public context; do not use a private address or personal location.
- Optional `context_retrieval_enabled`: boolean, default `false`; may be enabled only when the area and source policy have been approved.

The server must not accept arbitrary code or arbitrary executable paths in the configuration.

A successful source registration returns the created source metadata.

#### Clip upload

Content type: multipart/form-data

Fields:

- name
- file
- Optional `context_area_label`: coarse, approved public area label; never a private address or personal location.
- Optional `context_retrieval_enabled`: boolean, default `false`; only enabled after the area and source policy are approved.

When an uploaded clip enables source-level context, the initial configured topic is `public_notice`; the context-refresh request may select only topics configured for that source. This default avoids adding an unconfigured topic field to the upload form.

The endpoint must validate the file size, supported format, actual content, and decoding feasibility where practical.

It must create the required source and evidence metadata and enqueue processing without keeping the HTTP request open throughout inference.

Return 202 Accepted when processing has been queued.

The response must include:

- source_id
- evidence_id
- job_id
- status

If upload persistence succeeds but job creation fails, the implementation must either roll back the operation safely or record a recoverable state. It must not leave an apparently successful upload with no way to inspect its processing status.

#### Source response

Return:

- id
- name
- source_type
- status
- last_processed_at, if available
- created_at
- Safe processing status information
- `context_area_label`, if configured
- `context_retrieval_enabled` and a safe context-feature status

Never return credentials or private storage paths.

#### Reprocessing

Reprocessing must use already registered, authorized source content. It must not create duplicate incident records where the same source events are recognized.

A reprocessing endpoint is not required for the initial demonstration if no reprocessing control is implemented.

#### Context refresh request

The caller must be authorized for the source, and the source must have `context_retrieval_enabled = true` plus an approved `context_area_label`. The request must not accept arbitrary URLs, raw page HTML, evidence files, personal data, or provider credentials.

Request fields may include:

- `topics`: optional subset of up to three configured topics from `weather_advisory`, `transport_disruption`, `public_notice`, `public_event`, `emergency_advisory`, and `other`.
- `time_window_hours`: integer from 1 to 168, default 24.

The backend derives the search query from the stored approved area and allowlisted topics, enforces result limits/cooldowns, and creates a `context_enrichment` job. Return 202 Accepted with `source_id`, `job_id`, and `status`. The job result is retrieved through the existing job and context-list endpoints; do not hold the HTTP request open while TinyFish executes.

The worker caps a refresh at three topics, five bounded page fetches, and 150 seconds of provider work; a nonempty configured TinyFish allowlist and backend secret are required. Completed empty searches remain completed with zero saved items; provider or configuration failures become failed jobs. Duplicate context rows use the source/dedupe constraint and do not change detector/review state.

#### Context list response

Return a bounded, paginated collection. Each item may include `id`, `topic`, `title`, `publisher`, `source_domain`, `source_url`, `summary`, `published_at`, `retrieved_at`, `freshness_status` (`current`, `stale`, `unknown`), and a `processing_job_id` or other safe provenance reference. Never expose the raw provider response, unbounded page content, or API key. An unknown publication time must remain unknown.

#### Context retrieval semantics

- A successful refresh with no matching results is different from a failed refresh.
- A failed provider call must be visible as a failed context job and must not block video processing or incident review.
- Context items are attributed candidate information, not verified incident facts.
- Context does not change incident status, detector score, reliability metrics, or review outcome.
- Context list and refresh endpoints require resource-level authorization and bounded filtering/pagination.

---

### 4.7 Background Jobs and System Status

| Method | Endpoint | Purpose | Access |
|---|---|---|---|
| GET | /api/v1/jobs/{job_id} | Inspect processing-job status | Authenticated and authorized |
| GET | /api/v1/system/status | Inspect source and processing health | Authenticated; details restricted by role |
| GET | /health/live | Application liveness check | Internal/platform |

The existing job endpoint also returns the state of `context_enrichment` jobs. The public API must not expose TinyFish credentials, raw provider payloads, or internal diagnostic detail.
| GET | /health/ready | Readiness check for required dependencies | Internal/platform |

#### Job states

- pending
- running
- completed
- failed

#### Job response

Include:

- id
- job_type
- status
- created_at
- started_at, if available
- finished_at, if available
- attempt_count
- Safe error_code and error_summary, if failed
- Relevant output references or result metadata

Do not expose stack traces, raw exception contents, private paths, or other users' job data.

For `source_processing`, an authorized job owner or technical administrator may receive bounded measured video-quality fields and, when `DETECTOR_BACKEND=opencv_zoo`, object-observation summaries with detector/version/taxonomy provenance. Object summaries contain only class, sample count, and mean model score; no bounding boxes or frame bytes are returned. Face-region output is a count only. These values are observations, not incident classifications, proof that an event occurred, or reliability metrics. A successful job with no object observations does not establish that no incident occurred. Result keys are allowlisted by the API; private storage paths and arbitrary worker metadata are never serialized.

#### Health checks

/health/live answers whether the application process is running.

/health/ready verifies that the dependencies required to serve the configured application are ready.

Worker status must be monitored separately. A healthy HTTP process does not prove that video inference is working.

---

### 4.8 Reliability

| Method | Endpoint | Purpose | Access |
|---|---|---|---|
| GET | /api/v1/reliability/summary | Retrieve available reliability metrics | Authenticated |

Optional query parameters:

- evaluation_id
- start_at
- end_at
- source_id

Only implement a filter when its data and semantics are …2632 tokens truncated…amples.

---

## 7. Pagination, Filtering, and Sorting

### 7.1 Pagination

Incident, source, job, and evaluation list endpoints must use bounded pagination when the result set can grow.

Use page and page_size for the MVP unless actual query patterns require cursor pagination.

Rules:

- page starts at 1.
- page_size must be positive.
- The server defines and enforces a maximum page size.
- Results must have stable ordering, including a tie-breaker such as ID.
- Total counts may be omitted when expensive or unnecessary.

### 7.2 Example List Response

    {
      "items": [],
      "page": 1,
      "page_size": 25,
      "has_more": false
    }

The response may include total_count when it is available and appropriate.

### 7.3 Filtering

Only explicitly supported filter fields are accepted.

For incidents, these include:

- Event-time range.
- Source ID.
- Detection category.
- Review status.

For evaluations, supported filters may include dataset ID and status.

Validate timestamp ordering, identifier formats, and allowed status values.

### 7.4 Sorting

The backend maintains an allowlist of sorting fields and directions.

Do not interpolate user-supplied column names, sort expressions, or other SQL fragments into database queries.

### 7.5 Empty Results

Return a successful list response with an empty items array when no records match. An empty result is not an API failure.

The frontend distinguishes a genuinely empty dataset from a filter that produces no matches.

---

## 8. External APIs and Integrations

### 8.1 MVP Integration Policy

The primary integrations are internal:

- FastAPI to PostgreSQL.
- FastAPI and worker to private evidence storage.
- Worker to the selected local detector/model implementation.
- Worker to the dataset and annotation storage used for evaluation.

TinyFish is a separate, feature-flagged public-context integration. It is never part of the video-inference path and can be unavailable without degrading the core incident workflow.

### 8.2 TinyFish Search and Fetch Integration

Use the official TinyFish REST endpoints from the backend/worker only:

- Search: `GET https://api.search.tinyfish.ai` with `X-API-Key` and bounded query parameters.
- Fetch: `POST https://api.fetch.tinyfish.ai` with `X-API-Key`, `Content-Type: application/json`, and a bounded `urls` array; request Markdown format for the MVP.

Search should be used to discover candidate public pages. Fetch should read selected source URLs before the item is presented as source-grounded context where feasible. Use official, relevant domains when configured; do not trust a URL just because Search returned it. Fetch requests must stay within the provider's current request limit and the lower SafeCity-configured limit. Check the current official documentation for the exact provider response schema before implementation:

- https://docs.tinyfish.ai/search-api/reference
- https://docs.tinyfish.ai/fetch-api/reference

#### Security and reliability requirements

- Read `TINYFISH_API_KEY` only from backend configuration and send it in the `X-API-Key` header. Never expose it through the frontend, response bodies, logs, or error traces.
- Never send CCTV footage, frames, evidence bytes, personal data, credentials, private URLs, or internal institutional information to TinyFish.
- Validate all returned/fetched URLs using an allowlist, `http`/`https` only, no embedded credentials, and no private, loopback, link-local, or metadata-service destinations. Do not permit callers to supply arbitrary target URLs.
- Set timeouts, response-size/result limits, rate-aware backoff and refresh cooldowns. Bound query scope by source area, allowed topics, and time window.
- Treat retrieved text as untrusted data and ignore any instructions it contains. Do not execute code, perform actions, or follow arbitrary URLs in page content.
- Normalize provider data into typed internal schemas. Store and return only a bounded source-grounded excerpt and attribution metadata.
- Show source URL, publisher/domain, retrieval time, publication time when provided, and current/stale/unknown freshness. Never invent publication times or imply that a source is verified just because a request succeeded.
- Use deterministic provider mocks for ordinary tests. Network-dependent integration tests must be opt-in.
- Agent/browser automation is outside MVP scope and requires a separately approved use case.

### 8.3 Detector Integration

The selected detector should be invoked through an internal detector adapter, not through an undocumented browser-to-model request.

The adapter must return normalized detections with source timestamps where supported, detector identity and version, and the original score semantics.

Detector failures must be converted into explicit processing errors. Invalid or absent detector output must not be converted into a positive incident claim.

If a simulated detector is used, the resulting source and events must remain clearly identified as simulated.

### 8.4 Object Storage

Object storage is optional and depends on the approved deployment.

If used:

- Keep credentials on the server or worker.
- Restrict access to private objects.
- Verify upload and download behavior.
- Use short-lived signed URLs only after authorization.
- Avoid logging full signed URLs.
- Handle missing objects and provider outages as evidence availability failures.

### 8.5 No External Notifications or Dispatch

Automated notifications, emergency-service dispatch, facial-recognition APIs, and other excluded services must not be added to the MVP.

### 8.6 Webhooks

No inbound or outbound external webhooks are required for the MVP.

The local detector and background worker communicate through the internal processing architecture and shared database, not through a public detector callback endpoint.

If a future approved integration requires webhooks, the implementing team must separately define:

- The exact event schema.
- An authenticated sender identity.
- Signature verification over the raw request body, using a securely managed secret or supported asymmetric signature.
- Replay protection, such as a timestamp and event identifier.
- Idempotent processing.
- Strict payload size and content validation.
- A timeout and retry policy.
- A documented response contract.
- Logging that excludes secrets and private media.

Do not create a generic public webhook endpoint in anticipation of hypothetical integrations.

---

## 9. Rate Limiting and Resource Controls

Rate limits protect the application from accidental overload and abusive requests.

### 9.1 Endpoint Categories

Apply stricter limits to:

- Login attempts.
- Source and video uploads.
- Processing-job creation.
- Evaluation-job creation.

Ordinary authenticated read operations may use more permissive limits.

### 9.2 Proposed Initial Limits

The following are starting configuration suggestions, not established product requirements:

| Operation | Proposed initial limit |
|---|---|
| Login | 10 attempts per minute per source IP, with account-aware protections where practical |
| Upload | 10 requests per minute per authenticated administrator, subject to file-size limits |
| Processing-job creation | 10 requests per minute per authorized user |
| Evaluation creation | 5 requests per minute per authorized user |
| Read endpoints | 120 requests per minute per authenticated user |

These limits must be adjusted after observing actual use and deployment constraints.

Do not use an IP-only limit as the sole login defense. Shared institutional networks may represent many legitimate users.

### 9.3 Implementation

For a single-instance MVP, an in-process limiter can be sufficient for initial development, but its limits reset with process restarts and are not shared across replicas.

If the application is deployed across multiple web instances, use a shared rate-limit mechanism or enforce suitable limits at the trusted reverse-proxy or hosting boundary.

Do not introduce Redis solely to implement rate limiting before a multi-instance requirement exists.

The initial in-process login limiter counts attempts per normalized account and per source IP (10 per account and 30 per IP within 60 seconds). It is process-local and resets on restart; a multi-instance deployment must apply the documented trusted-proxy/shared limiting boundary.

The current single-instance defaults also limit source registration/upload to 10 requests per minute per authenticated technical administrator, source processing requests to 10 per minute per authenticated technical administrator, and evaluation creation to 5 per minute per authenticated technical administrator. These are process-local, bounded in-memory sliding windows and return 429 with `Retry-After`. Public-context Search/Fetch uses its separate per-user cooldown. These controls reset on process restart and are not a distributed limit; shared deployment must enforce equivalent controls at its trusted proxy or use a shared limiter only when multi-instance deployment is selected.

### 9.4 Rate-Limit Response

When a limit is exceeded, return 429 Too Many Requests with a safe error body.

Where supported, include Retry-After so the client can wait before retrying.

### 9.5 Upload Limits

The backend must enforce upload size and supported media types independently of frontend controls and proxy settings.

Use processing time and resource limits appropriate to the selected decoder and detector. Large files or expensive inference must not be allowed to exhaust application resources without bounds.

---

## 10. Required Environment Variables

The application must load environment configuration through a validated backend configuration module.

Only variables required by the selected implementation should be enabled. No secret may be exposed in a frontend bundle.

| Variable | Required | Purpose |
|---|---|---|
| APP_ENV | Yes | Select development, test, staging, or production behavior |
| DATABASE_URL | Yes | PostgreSQL connection string; secret |
| SESSION_TTL_SECONDS | Yes | Session lifetime |
| SESSION_IDLE_TTL_SECONDS | Yes | Idle timeout; must not exceed absolute session lifetime |
| SESSION_CSRF_SECRET | Yes in production | At least 32 random characters; HMAC key for CSRF tokens |
| COOKIE_SECURE | Yes | Require secure cookies in production |
| COOKIE_SAMESITE | Yes | Session-cookie SameSite policy |
| CSRF_ALLOWED_ORIGINS | Yes for cookie-authenticated browser deployments | Approved origins for state-changing browser requests |
| CORS_ORIGINS | Conditional | Explicit frontend origins when cross-origin requests are needed |
| PUBLIC_APP_ORIGIN | Yes | Canonical application origin used for origin checks and URL construction |
| LOCAL_MEDIA_ROOT | Yes when local storage is used | Private media-storage directory |
| STORAGE_BACKEND | Yes | Select the configured storage implementation |
| MAX_UPLOAD_BYTES | Yes when uploads are supported | Maximum permitted upload size |
| MAX_UPLOAD_DURATION_SECONDS | Yes when video uploads are supported | Maximum decoded video duration |
| SUPABASE_URL | Required when Supabase Storage is selected | Backend-only project URL; HTTPS required |
| SUPABASE_SERVICE_ROLE_KEY | Required when Supabase Storage is selected | Private backend secret; never expose to Vite or the browser |
| SUPABASE_STORAGE_BUCKET | Required when Supabase Storage is selected | Private evidence bucket name; public access disabled |
| DETECTOR_BACKEND | Yes when detection is enabled | Select installed detector or simulated implementation |
| DETECTOR_VERSION | Yes when a detector is selected | Version identifier for reproducibility |
| WORKER_POLL_INTERVAL_SECONDS | Yes for database polling worker | Delay between job-queue checks |
| WORKER_MAX_ATTEMPTS | Yes | Maximum processing attempts |
| LOG_LEVEL | Yes | Logging verbosity |
| TINYFISH_CONTEXT_ENABLED | Yes | Feature flag for public context retrieval; false by default when not configured |
| TINYFISH_API_KEY | Required only when TinyFish context is enabled | TinyFish Search/Fetch API key; secret, backend/worker only |
| TINYFISH_REQUEST_TIMEOUT_SECONDS | Yes when enabled | Maximum provider request duration |
| TINYFISH_MAX_RESULTS_PER_REFRESH | Yes when enabled | Maximum search candidates and fetched URLs per refresh; enforce a conservative MVP bound |
| TINYFISH_CONTEXT_TTL_SECONDS | Yes when enabled | Freshness/cache window used to mark stored context current or stale |
| TINYFISH_ALLOWED_DOMAINS | Conditional | Server-side allowlist of approved public source domains when configured |

Additional settings may be required for a chosen model or object-storage provider.

### 10.1 Secret Requirements

- Do not commit actual .env files.
- Keep real database credentials and other secrets in the deployment environment or a secret manager.
- Include placeholders only in .env.example.
- Do not prefix backend secrets with frontend-exposed environment-variable prefixes.
- Do not return environment variables through any API endpoint.
- Fail startup clearly when critical production configuration is missing or invalid.

### 10.2 Frontend Configuration

If VITE_API_BASE_URL is used, it is public configuration and must contain no secrets. It should point to the API's public origin or base path.

Session cookies, database URLs, storage credentials, model secrets, and internal network addresses must remain backend-only.

---

## 11. Data Privacy and Evidence Protection

### 11.1 Minimization

The API must return only information required for the user's task.

Do not expose:

- Password hashes.
- Session-token hashes.
- Database connection details.
- Private storage paths.
- Internal exception details.
- Raw uploaded video content in JSON responses.
- Unnecessary personal information.

### 11.2 Evidence Authorization

Every evidence metadata and content request must be authorized server-side.

A valid evidence ID is not permission to access its content.

The backend must verify the evidence association and the requesting user's access rights before streaming the file or issuing a temporary storage URL.

### 11.3 Privacy-Aware Logging

Logs may record resource IDs, job IDs, request IDs, status transitions, and sanitized error codes.

Logs must not contain passwords, session tokens, raw video frames, unnecessary personal information, or full signed media URLs.

### 11.4 Retention

The media-retention period requires approval under the PRD.

Until approved, use authorized development or evaluation data only and do not implement automatic destructive retention rules that could erase evidence unexpectedly.

Deletion must coordinate storage removal with database metadata and any applicable evaluation or review requirements.

### 11.5 Product Safety Boundary

The API must not implement identity-based tracking, facial recognition, individual criminality scores, automated accusations, or autonomous punitive actions.

Automated detections remain candidate events for human review.

---

## 12. Failure Handling and Fault Tolerance

### 12.1 Database Unavailability

If PostgreSQL is unavailable:

- Return 503 Service Unavailable where an operation cannot proceed.
- Do not report a review as saved unless its transaction committed successfully.
- Do not acknowledge a processing job as accepted unless the job and required references were persisted.
- Log the sanitized failure with a request identifier.
- Allow safe retries once service is restored.

### 12.2 Storage Unavailability

If evidence storage is unavailable:

- Return or display an evidence-unavailable state as appropriate.
- Keep other incident metadata accessible when possible.
- Do not return an empty successful media response that looks like valid evidence.
- Record the storage failure for an authorized administrator.
- Avoid regenerating duplicate evidence during retries.

### 12.3 Detector Failure

If inference fails or returns invalid output:

- Mark the processing job failed when no valid completion is possible.
- Persist safe diagnostics.
- Do not create an unsupported positive incident conclusion.
- Do not claim that a detector returned a negative result when it did not execute successfully.

A successfully completed job may still have a documented partial result if the implementation explicitly supports partial processing and reports its limitations.

### 12.4 Worker Failure

If the worker stops unexpectedly:

- The job must not remain indefinitely in an apparently active state.
- The worker must recover or fail abandoned jobs according to its lease or timeout strategy.
- Retried work must not create duplicate incident, evidence, or metric records.
- A failed job must be inspectable by an authorized technical administrator.

### 12.5 Evaluation Failure

If one or more assets fail:

- Report successful, failed, excluded, and eligible asset counts distinctly.
- Preserve the evaluation's failure or partial-result state.
- Do not count failed assets as event-free video.
- Do not publish an unqualified metric if exclusions materially affect the denominator.
- Preserve the dataset and model metadata used for the run.

### 12.6 Client Retry Behavior

The frontend must avoid blindly retrying non-idempotent operations such as review creation, source uploads, or evaluation creation.

Where automatic retries are necessary, use an idempotency key or another documented deduplication mechanism.

Retries must not create duplicate side effects.

### 12.7 Timeouts

Apply documented request timeouts for database and storage operations. Video inference, full evaluation, and TinyFish retrieval belong in the worker rather than in long-running HTTP requests.

A client timeout must not be interpreted as proof that a server-side operation failed; the client should retrieve the resource or job status before submitting the same operation again.

### 12.8 TinyFish Failure Handling

- Missing key or disabled configuration returns an explicit unavailable/disabled context state; it does not prevent application startup unless deployment policy explicitly requires the integration.
- Provider timeout, 401/403, 429, 5xx, malformed response, and per-URL fetch failure are logged as sanitized diagnostic categories and reflected in the job status.
- Back off on rate limits and transient service errors; do not retry unauthorized, invalid, or malformed requests indefinitely.
- Keep existing context items with their original retrieved timestamps when a later refresh fails. Do not update timestamps to make stale entries look fresh.
- Distinguish no results from retrieval failure. Neither state implies the area is safe.
- TinyFish outages must not change detection behavior or block incident review, evidence playback, authentication, or evaluation of labeled video.

---

## 13. API Documentation and Testing

### 13.1 OpenAPI

FastAPI's OpenAPI document must describe:

- Endpoint methods and paths.
- Authentication requirements.
- Request schemas.
- Response schemas.
- Query parameters.
- Status codes.
- Error response formats.
- Supported filtering and pagination.

Interactive API documentation should be available during development and restricted or disabled in production unless intentionally exposed.

### 13.2 Contract Tests

Automated tests must cover:

- Successful and failed authentication.
- Role enforcement and direct unauthorized endpoint requests.
- Incident filtering and pagination.
- Incident detail and evidence association.
- Evidence access denial.
- Review submission, persistence, and duplicate handling.
- Job acceptance and job-status retrieval.
- Source-upload validation and processing errors.
- Evaluation creation and result retrieval.
- Metric availability and undefined denominators.
- Rate-limit responses.
- Safe error formatting.
- Session expiration and CSRF validation.
- Database or storage unavailability.
- Context list/refresh permissions, source enablement validation, bounded query fields, and context freshness semantics.
- TinyFish success, empty results, stale results, missing publication time, timeout, rate limit, malformed payload, and disabled configuration using mocked provider responses.
- Verify that external context cannot create an incident, change detector/reliability fields, or overwrite a human review.

### 13.3 Evaluation Tests

Given a deterministic labeled dataset and fixed detector outputs, the evaluation API must return reproducible metrics under the same documented configuration.

A simulated detector may be used for contract tests, but its outputs must be labeled simulated and excluded from real-world performance claims.

### 13.4 Compatibility

Any breaking change to request fields, response shapes, status semantics, or error conventions must be reflected in this document and handled through the versioned API policy.

Do not silently change the meaning of a response field while preserving its name.

---

## 14. MVP API Checklist

Before the API is considered ready, verify that:

- [ ] Authentication and logout work through secure server-managed sessions.
- [ ] The current-user endpoint returns no secrets.
- [ ] Role and resource authorization are enforced server-side.
- [ ] Incident listing and detail endpoints support the required operator workflow.
- [ ] Detector predictions, reliability assessments, and human review outcomes remain separate.
- [ ] Review submission persists data transactionally.
- [ ] Evidence endpoints restrict media access and support practical video playback.
- [ ] The selected source-ingestion mode is implemented and accurately labeled.
- [ ] Long-running processing returns a job identifier rather than blocking the HTTP request.
- [ ] Evaluation requests reference valid, versioned datasets.
- [ ] Reliability metrics include availability state and evaluation context.
- [ ] Undefined metrics are not represented as zero.
- [ ] Pagination, filters, and sorting are bounded and validated.
- [ ] All API errors follow a consistent schema.
- [ ] Upload limits, authentication limits, and appropriate rate controls are implemented.
- [ ] The API has no unnecessary external webhook or notification endpoints.
- [ ] TinyFish Search/Fetch is called only by the backend/worker and only for approved public context.
- [ ] Context refresh runs asynchronously through a `context_enrichment` job and has bounded timeouts, counts, and retry behavior.
- [ ] Context items preserve source URL, topic, publisher/domain, retrieved time, publication time when available, and freshness status.
- [ ] TinyFish disabled/unavailable states do not block incident review or video processing.
- [ ] Secrets never enter client bundles, JSON responses, or logs.
- [ ] Failure handling covers database, storage, detector, and worker failures.
- [ ] OpenAPI and automated contract tests reflect the implemented contract.

---

## 15. Final API Definition

The SafeCity AI API is a versioned REST interface served by FastAPI. It manages authentication, incidents, evidence access, human reviews, source ingestion, processing jobs, reliability metrics, evaluations, and system health.

PostgreSQL is the authoritative source for workflow state. Video processing and evaluation execute asynchronously through a background worker. Media remains in private storage and is exposed only through authorized evidence access.

The MVP uses one configured detector or a clearly labeled simulated source and calculates video-detection metrics only from valid, documented inputs. TinyFish Search and Fetch provide a separate, feature-flagged path for attributed public-web context; this provider receives no surveillance media or personal data and cannot determine incident truth or trigger consequential actions. No public webhook is required.

**The defining API principle is simple: every operation must be authenticated and authorized when required, every result must communicate its actual state, and every reliability claim must remain traceable to its evidence and evaluation context.**
