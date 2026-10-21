# SafeCity AI — System Architecture

**Document:** ARCHITECTURE.md  
**Version:** 1.0  
**Status:** Proposed architecture — pending approval of key technical decisions  
**Product:** SafeCity AI  
**Source of truth:** PRD.md and DESIGN.md

---

## 1. Architecture Overview

### 1.1 Objective

SafeCity AI must provide a secure, maintainable web application for reviewing surveillance-video incident detections, assessing video reliability, inspecting supporting evidence, recording human review outcomes, and evaluating detection performance.

The architecture must support the MVP without introducing unnecessary infrastructure. It must also allow the selected detection model, video-storage implementation, and deployment environment to change without requiring a complete application rewrite.

### 1.2 Architectural Principles

1. **Modular monolith:** Build one backend application with clearly separated modules instead of multiple independently deployed business services.
2. **One primary database:** Store application metadata, incident records, review outcomes, processing jobs, and evaluation results in PostgreSQL.
3. **Python for video processing:** Keep video decoding, quality assessment, detection, and evaluation within the Python ecosystem.
4. **Explicit interfaces:** Separate the core incident workflow from detector-specific and storage-specific implementations.
5. **Human-reviewed decisions:** Never treat model-generated predictions as authoritative incident conclusions.
6. **Evidence integrity:** Preserve the association between an incident and its source evidence.
7. **Privacy by default:** Restrict video access, minimize unnecessary personal data, and avoid identity-based surveillance.
8. **Observable failures:** Record processing errors and expose understandable statuses to authorized users.
9. **Measured reliability:** Calculate metrics from documented evaluation data rather than fabricated or hardcoded values.
10. **MVP before scale:** Optimize for a reliable, demonstrable single-institution deployment. Introduce additional infrastructure only when demonstrated requirements justify it.

### 1.3 Recommended Deployment Architecture

The MVP should use:

- One React web frontend.
- One FastAPI backend.
- One PostgreSQL database.
- One background processing worker using the same backend codebase.
- Local or application-managed video storage for development, with a storage interface that can support durable object storage.
- One configured detection pipeline or a clearly labeled simulated detector.

The worker is a separate execution process, not a separate microservice with its own business logic, API, or database.

### 1.4 Logical Architecture

The intended request and processing flow is:

1. A web browser uses the React application for overview, incident review, reliability, and system status.
2. The browser communicates with the FastAPI application through an HTTPS JSON API.
3. FastAPI authenticates and authorizes requests, validates payloads, and invokes application services.
4. PostgreSQL stores incidents, users and sessions, assessments, reviews, jobs, datasets, and evaluation results.
5. Evidence storage holds video clips and extracted frames; PostgreSQL stores their metadata and references.
6. The background worker reads queued work, processes video, invokes the detector adapter, runs reliability checks, creates evidence references, and calculates evaluation metrics.
7. The frontend retrieves resulting records and displays their actual processing states.

The API and worker may use the same application image and codebase while running as separate processes.

---

## 2. Recommended Technology Stack

The following stack is the recommended default for the initial implementation. It resolves the PRD's technology-stack decision provisionally without assuming that the detector or benchmark dataset has already been selected.

### 2.1 Frontend

| Technology | Purpose | Reason |
|---|---|---|
| React | Build the user interface | Component-based UI suits incident lists, evidence review, dashboards, and shared controls. |
| TypeScript | Type-safe application development | Helps prevent inconsistent handling of incident states and API response data. |
| Vite | Development server and production build | Provides a straightforward frontend build workflow without a full-stack framework. |
| React Router | Client-side navigation | Supports overview, incident list, incident detail, reliability, and system-status screens. |
| TanStack Query | Server-state fetching and caching | Handles loading, error, retry, invalidation, and refresh behavior for API data. |
| CSS variables and CSS Modules | Styling and design-system implementation | Implements the reusable tokens in DESIGN.md without requiring a large UI framework. |
| Recharts | Data visualization | Supports simple reliability charts with axes, tooltips, and legends. Use only where charts add value. |
| Lucide React | Interface icons | Provides a consistent icon set for navigation and status controls. |
| Vitest and React Testing Library | Frontend tests | Tests components, interactions, loading states, and review workflows. |

**Frontend rules:**

- Keep API access in a shared client module.
- Define TypeScript types for API responses and request payloads.
- Do not duplicate backend business logic in the browser.
- Do not store authoritative review outcomes, permissions, or detector results only in client state.
- Use shared components and design tokens from DESIGN.md.
- Avoid additional UI libraries when native components and the existing design system are sufficient.

### 2.2 Backend

| Technology | Purpose | Reason |
|---|---|---|
| Python 3.12 | Backend runtime | Provides compatibility with the Python video-processing and ML ecosystem. |
| FastAPI | HTTP API and application server | Provides request validation, typed endpoints, and automatically generated OpenAPI documentation. |
| Pydantic v2 | Request and response schemas | Validates external inputs and defines explicit API contracts. |
| SQLAlchemy 2 | Database access | Provides a maintainable ORM and transaction support. |
| Alembic | Database migrations | Tracks and applies schema changes safely. |
| PostgreSQL | Persistent application database | Supports relational data, transactions, indexing, and concurrent API and worker access. |
| Psycopg 3 | PostgreSQL driver | Connects the Python application to PostgreSQL. |
| pytest | Backend testing | Supports unit, API, integration, and regression tests. |
| HTTPX | API test client and HTTP integration testing | Works with FastAPI testing workflows and simulated external HTTP calls. |

Use maintained, mutually compatible dependency versions and pin them through the project's chosen lockfile or dependency-management workflow.

### 2.3 Video Processing and AI

| Technology | Purpose | Recommendation |
|---|---|---|
| OpenCV | Video decoding and measurable image-quality checks | Use for initial video processing where supported. |
| NumPy | Frame and numeric operations | Add when required by selected processing steps. |
| Selected detector or anomaly model | Candidate incident detection | Decide after reviewing event categories, input format, hardware, and available test data. |
| PyTorch | Model inference | Add only if the selected model requires it. |
| scikit-learn | Optional evaluation utilities | Add only if useful; basic metric calculations can be implemented directly and tested. |

Do not install every library in this table by default. In particular, do not add a large deep-learning dependency until a specific model has been selected.

UCF-Crime should be treated as a research dataset and benchmark context, not as a ready-to-run production detector.

### 2.4 Development and Deployment

| Technology | Purpose |
|---|---|
| Docker | Reproducible application packaging |
| Docker Compose | Local development with PostgreSQL and application processes |
| PostgreSQL service | Persistent application state |
| Environment variables | Deployment-specific settings and secrets |
| pytest and Vitest | Automated tests in development and CI |
| GitHub Actions | Optional automated testing and build verification |

No Kubernetes, Redis, Kafka, vector database, or distributed microservice infrastructure is required for the initial MVP.

### 2.5 Decisions Requiring Approval

The proposed stack should be reviewed against the existing repository before implementation.

The following choices remain approval-dependent:

- Exact detector or anomaly-detection implementation.
- Evaluation dataset and its licensing.
- Hosting provider and deployment environment.
- Local-volume versus object-storage deployment for video.
- Whether prerecorded clips, a simulated event feed, or both are used for the first demonstration.

---

## 3. Frontend Architecture

### 3.1 Responsibilities

The frontend is responsible for:

- Displaying incidents and their associated evidence.
- Showing detector output separately from reliability assessments and human reviews.
- Collecting review decisions.
- Displaying metric results returned by the backend.
- Displaying processing statuses and errors.
- Enforcing the interaction and visual rules in DESIGN.md.
- Supporting prescribed loading, empty, failed, and uncertain states.

The frontend must not directly access PostgreSQL, local storage paths, detector files, or unrestricted video-storage locations.

### 3.2 Application Structure

Organize the frontend around product features rather than grouping every file by generic technical type.

Recommended feature areas:

- **overview:** Dashboard summaries and current operational state.
- **incidents:** Incident listing, filters, detail view, and review controls.
- **reliability:** Metrics, evaluation summaries, and charts.
- **sources:** Source and processing status.
- **evaluations:** Dataset and evaluation-run views where a separate interface is needed.
- **components:** Shared navigation, buttons, status labels, tables, feedback messages, and evidence components.
- **lib:** API client, shared types, and cross-feature utilities.
- **styles:** Global CSS and design tokens.

### 3.3 API Client

All application requests must pass through a shared API client.

The client must:

- Use the common API base path.
- Send requests with the required session credentials.
- Parse documented API responses.
- Handle authentication expiration consistently.
- Normalize API errors for presentation in the interface.
- Avoid retrying non-idempotent operations blindly.
- Support cancellation of obsolete list and detail requests where appropriate.

Do not let individual page components implement their own inconsistent error parsing or request behavior.

### 3.4 Server State and UI State

Keep server state distinct from transient interface state.

**Server state includes:**

- Incidents.
- Review records.
- Reliability assessments.
- Processing statuses.
- Evaluation results.
- Authorized-user information.

**UI state includes:**

- Current filters.
- Selected table row.
- Open dialog.
- Active tab.
- Unsaved form selection.

TanStack Query should manage server-state caching and invalidation. React component state should manage temporary UI interactions.

The frontend must not treat cached data as proof that a server-side review update succeeded.

### 3.5 Routing

Use React Router with routes corresponding to the screens in DESIGN.md.

| Route | Purpose |
|---|---|
| /login | Authentication |
| / | Overview dashboard |
| /incidents | Incident list |
| /incidents/:incidentId | Incident details and evidence review |
| /reliability | Reliability metrics |
| /status | Sources and processing status |
| /evaluations/:evaluationId | Evaluation details, if implemented as a separate screen |

Routes that contain incident data or administrative functionality must be protected.

Client-side route protection improves the experience but does not replace backend authorization.

### 3.6 Design-System Integration

Implement the colors, spacing, typography, semantic states, responsive layouts, and reusable components specified in DESIGN.md.

The frontend should have shared components for at least:

- Application shell and navigation.
- Page heading.
- Button variants.
- Status label.
- Incident table.
- Filter controls.
- Evidence player or frame viewer.
- Evidence metadata.
- Reliability assessment panel.
- Review outcome controls.
- Metric display.
- Chart container.
- Loading indicator.
- Empty state.
- Inline error message.
- Toast notification.

Do not create a new component variant for every individual page if the same behavior can be represented by an existing shared component.

---

## 4. Backend Architecture

### 4.1 Modular Monolith

The backend is a single FastAPI application organized into modules with explicit responsibilities.

A request should flow through:

1. API route and request validation.
2. Authentication and authorization.
3. Application service.
4. Repository or database-access function.
5. Database transaction or storage adapter, where needed.
6. Response-schema validation and serialization.

The route layer must remain thin. Business rules should not be implemented directly inside request handlers or duplicated between endpoints.

### 4.2 Core Modules

#### Authentication and Authorization

Responsible for:

- User authentication.
- Session creation and invalidation.
- Resolving the current user.
- Checking roles and resource permissions.

#### Incident Management

Responsible for:

- Normalizing candidate detections.
- Creating incident records.
- Applying source-event deduplication.
- Returning incident lists and details.
- Managing review status independently from the original prediction.

#### Reliability Assessment

Responsible for:

- Applying supported video-quality checks.
- Recording evidence-sufficiency results.
- Recording uncertainty reasons.
- Maintaining assessment versions.
- Avoiding fabricated quality measurements.

#### Evidence Management

Responsible for:

- Registering evidence metadata.
- Resolving storage references.
- Checking permissions before serving evidence.
- Verifying evidence availability.
- Keeping evidence associated with the correct incident.

#### Review Management

Responsible for:

- Validating review outcomes.
- Persisting reviewer decisions.
- Preserving model predictions.
- Recording review timestamps and reviewer IDs.
- Maintaining review history when implemented.

#### Evaluation

Responsible for:

- Loading ground-truth labels.
- Matching predictions to reference events.
- Calculating metrics.
- Recording model versions and evaluation configuration.
- Returning traceable evaluation results.

#### Public Context Enrichment

Responsible for:

- Building bounded search queries from an explicitly configured source area, approved topic list, and time window.
- Calling TinyFish Search and Fetch through a typed provider adapter.
- Normalizing public-page metadata and bounded, source-grounded excerpts.
- Preserving attribution, publication time when available, retrieval time, freshness state, and provider errors.
- Keeping context items separate from detections, assessments, review outcomes, and reliability calculations.
- Deduplicating results and respecting per-source refresh limits.

The service must never send surveillance media, frames, credentials, personal data, private URLs, or non-public operational information to TinyFish.

#### Processing Jobs

Responsible for:

- Creating processing jobs.
- Claiming pending jobs.
- Tracking progress and status.
- Recording failures.
- Controlling retries and duplicate processing.

#### System Status

Responsible for:

- Reporting processing health.
- Reporting source status.
- Exposing safe diagnostic information to authorized administrators.
- Providing basic liveness and readiness checks.

### 4.3 Business Logic Boundaries

Keep the following distinctions explicit:

- **Detector prediction:** What the detection pipeline produced.
- **Reliability assessment:** What the system determined about video quality and evidence sufficiency.
- **Human review:** What an authorized reviewer concluded.
- **Evaluation result:** What a documented benchmark process calculated.

A human review must not rewrite the detector's original output. A failed reliability assessment must not be represented as a false alert. A model score must not automatically become an incident severity score.

### 4.4 Database Access

All database interaction must occur in the backend.

Use SQLAlchemy sessions with explicit transaction boundaries.

Recommended rules:

- Create one request-scoped database session per HTTP request.
- Give each worker job its own database session.
- Avoid sharing database sessions across threads or unrelated async tasks.
- Commit related record changes together.
- Roll back transactions after a failure.
- Avoid returning SQLAlchemy objects directly from API endpoints.
- Convert database entities to explicit response schemas.
- Use migrations for schema changes rather than modifying production tables manually.

### 4.5 Synchronous and Asynchronous Work

Operations such as listing incidents, reading incident metadata, and saving a review are ordinary request-response operations.

Video decoding, detection inference, evidence extraction, and dataset evaluation should run as background jobs.

The API should enqueue such work and return a job identifier. The frontend should retrieve job status rather than keeping an HTTP request open while a long video-processing operation runs.

For the MVP, a database-backed job queue and a single worker are sufficient. Do not introduce a dedicated message broker unless measured workload or operational requirements justify it.

---

## 5. AI and Video-Processing Architecture

### 5.1 Design Objective

The detection pipeline must be replaceable without coupling model-specific code to the core application.

The architecture must support an actual selected detector or a clearly labeled simulated source while ensuring that all resulting records follow the same internal event contract.

### 5.2 Detector Adapter

Define a common internal detector interface.

Its responsibilities are to:

- Accept a reference to a video or clip.
- Run the configured inference process.
- Return normalized candidate detections.
- Include event timestamps or intervals where supported.
- Return the original score and its documented meaning when available.
- Identify the detector and version.
- Report model-level failures explicitly.

Detector-specific preprocessing, output formats, and score interpretation must remain inside the adapter rather than leaking into incident-management endpoints.

### 5.3 MVP Detector Strategy

Implement one of these paths after approval:

**Option A — Selected real detector**

Integrate a concrete detector whose model weights, supported input format, license, inference requirements, and expected event categories have been verified.

**Option B — Simulated detection feed**

Use deterministic sample events for demonstrating the user interface and API workflow. Clearly label them as simulated and do not use their results as real-world model-performance evidence.

A simulated detector may validate application behavior, but it cannot demonstrate genuine computer-vision reliability improvements.

The implementation must not claim that a selected research dataset provides an inference pipeline when no compatible model has been implemented.

### 5.4 Video Ingestion Flow

For a prerecorded clip, the processing flow should be:

1. Validate the input file and its permitted source.
2. Create a processing-job record.
3. Store the video through the configured storage adapter.
4. Enqueue the job.
5. Have the worker claim the job.
6. Decode and validate the video.
7. Run the supported video-quality checks.
8. Invoke the detector adapter.
9. Normalize the detector outputs.
10. Associate candidate detections with source timestamps and evidence.
11. Apply the configured reliability and uncertainty rules.
12. Persist incidents, evidence references, reliability assessments, and processing outcomes.
13. Mark the job completed or failed.
14. Allow the frontend to refresh the resulting status and incident records.

When decoding or inference fails, the system must record the failure instead of fabricating an incident conclusion.

### 5.5 Video-Quality Assessment

The first implementation should use only measurable, supported checks.

Candidate checks include:

- Resolution.
- Blur or sharpness.
- Brightness or exposure.
- Missing frames and decoding failures.
- Occlusion or insufficient visible scene information, only if a reliable method is implemented.

The assessment module should produce:

- The check performed.
- The measured result, if available.
- Its status.
- The reason code where a check fails.
- The assessment version.

Do not create universal reliability percentages or pretend that image-quality measurements prove that a detection is correct.

### 5.6 Uncertainty and Abstention

Uncertainty rules must be explicit and testable.

The configured assessment may abstain or return an uncertain result when required evidence is unavailable or a supported quality criterion fails.

The system must preserve the distinction between:

- A detector producing no qualifying event.
- A detector producing an event with weak evidence.
- A quality check failing.
- A model failing to execute.
- An event being classified as false by a reviewer or evaluation procedure.

The correct outcome depends on the actual processing result and must not be guessed.

Thresholds and event categories are product decisions that require approval and evaluation.

### 5.7 Evidence Extraction

Evidence may include:

- A reference to the original clip.
- A short clip interval.
- Extracted image frames.
- The event's time interval.
- Source and detector metadata.

Evidence should be generated only when the relevant data is available.

Any extracted clip or frame must retain its association with the originating source and incident. Where supported, record a checksum or equivalent integrity metadata.

### 5.8 Evaluation Pipeline

Evaluation must be separate from ordinary incident review.

For a labeled dataset:

1. Load the versioned dataset and annotation set.
2. Process eligible clips using the selected detector.
3. Apply documented event-matching rules.
4. Compare predictions with ground-truth events.
5. Calculate true positives, false positives, false negatives, and supported metrics.
6. Record processing exclusions and failures.
7. Save the model version, configuration, dataset version, sample counts, and outcomes.

Use independently established labels. Do not derive ground truth from the predictions being evaluated.

### 5.9 Metric Calculation

For the MVP, calculations may be implemented directly in Python with unit tests.

Required calculations include:

- False alerts per eligible monitored-video hour.
- Precision.
- Recall.
- Detection delay where timestamps and event-matching rules permit it.
- Review time where reliable measurements are available.

Undefined metrics must be represented as unavailable, not zero.

Each result must refer to its evaluation scope and versioned inputs.

### 5.10 Model and Dataset Constraints

- Do not commit large model-weight files or private video datasets to Git.
- Document where model weights and datasets are obtained and how they are provisioned.
- Verify licenses and permitted usage.
- Pin or record model versions and relevant configuration.
- Do not download arbitrary weights automatically at application startup.
- Avoid sending surveillance footage to external AI providers unless separately approved.
- Keep inference configuration separate from the general application configuration.

---

## 6. Data Architecture

### 6.1 Primary Database

Use PostgreSQL as the single authoritative store for application metadata and workflow state.

PostgreSQL should store metadata and references to video files, not large video binaries.

### 6.2 Main Entities

| Entity | Responsibility |
|---|---|
| users | Application identity, role, and account state |
| sessions | Server-side login sessions |
| sources | Configured video, clip, or simulated-event sources |
| incidents | Normalized candidate detections and review status |
| evidence | Evidence metadata and storage references |
| reliability_assessments | Quality checks, uncertainty, and assessment reasons |
| reviews | Human review outcomes and reviewer attribution |
| processing_jobs | Job status, retries, and processing errors |
| evaluation_datasets | Dataset metadata, versions, and annotation references |
| ground_truth_events | Reference events and event time intervals |
| evaluation_runs | Evaluation inputs, configuration, and status |
| metric_results | Calculated metrics and their evaluation context |

Do not introduce additional entities solely to anticipate hypothetical future features.

### 6.3 Relationships

- One source can produce multiple incidents.
- An incident can reference multiple evidence records.
- An incident can have multiple reliability assessments over time.
- An incident can have multiple review records if review history is retained.
- A processing job can produce multiple incidents or reference a source-level processing operation.
- An evaluation dataset has versioned reference labels.
- An evaluation run references a dataset version and a detector version.
- A metric result belongs to an evaluation run.

These relationships should be represented through foreign keys and appropriate indexes.

### 6.4 Recommended Field Conventions

Use:

- UUID identifiers for primary keys where practical.
- Timezone-aware timestamps for all stored times.
- Explicit foreign keys.
- Enumerated or constrained values for stable states.
- JSONB only for supplementary, variable assessment measurements or configuration metadata.
- Separate typed columns for values used regularly in filters, joins, and metric calculations.

Do not put the entire incident or assessment object into a single unstructured JSON field.

### 6.5 State and Review Integrity

An incident should preserve its original normalized detection result.

Review status may change after human review, but the original prediction must remain intact.

Reliability assessments should remain associated with the detector and video context that produced them. Reprocessing with a different model or different assessment configuration must not silently overwrite historical evaluation results.

### 6.6 Database Transactions

Use transactions around logically related writes.

**Creating an incident:**

- Create the incident record.
- Save associated reliability-assessment metadata, when present.
- Register evidence references.
- Commit the logically consistent result.

**Saving a review:**

- Validate the request and authorization.
- Create a review record.
- Update the incident's current review status, if this denormalized field is used.
- Commit the changes together.

**Completing a processing job:**

- Save output records and failure metadata as appropriate.
- Update the job's status.
- Avoid marking a job completed before its required output records are committed.

### 6.7 Idempotency and Duplicate Prevention

A source event identifier should be used when available.

A uniqueness constraint on an appropriate source-event identity must prevent repeated delivery from creating duplicate incidents.

Where the detector provides no stable event identifier, derive a documented deduplication strategy suited to the specific source and event-matching behavior. Do not assume that two events with the same category or approximate timestamp are necessarily identical.

For processing jobs, prevent accidental duplicate execution from creating duplicate output records.

### 6.8 Indexing

Begin with indexes supporting common queries:

- Incident event timestamp.
- Incident source ID and timestamp.
- Incident review status and timestamp.
- Evidence incident ID.
- Assessment incident ID and creation timestamp.
- Review incident ID and review timestamp.
- Job status and creation timestamp.
- Evaluation dataset/version references.

Add indexes based on measured query needs, not speculation.

### 6.9 Migrations

Every persistent schema change must be represented by an Alembic migration.

Migrations should be version-controlled, reviewed, tested against representative data, and applied through a documented deployment process.

Do not automatically drop tables or erase production data during application startup.

---

## 7. Database Interaction and Storage Boundaries

### 7.1 Repository Pattern

Use a lightweight repository or equivalent database-access layer for entity-specific queries.

The purpose is to keep SQLAlchemy queries out of API routes and separate persistent storage from business rules.

Do not create generic repository frameworks or multiple abstraction layers when a simple module is sufficient.

### 7.2 Video Storage

Define a small storage interface supporting:

- Save an uploaded or generated file.
- Open or stream an authorized evidence file.
- Check whether an evidence object exists.
- Delete an object when an approved retention or cleanup operation requires it.
- Optionally calculate or verify an integrity checksum.

Implement local filesystem storage for development and a controlled MVP deployment when durable local storage is available.

If the deployment environment does not provide durable local storage, select an appropriate object-storage implementation before real evidence is uploaded.

### 7.3 Storage Key Safety

- Do not use user-supplied file paths as storage paths.
- Generate internal storage identifiers.
- Normalize and validate uploaded filenames and media metadata.
- Prevent directory traversal.
- Keep private evidence outside publicly served frontend directories.
- Never return unrestricted filesystem paths to the browser.

### 7.4 Serving Video

The backend must authorize evidence access before returning protected media.

For local or application-managed storage, stream the evidence through an authenticated endpoint. Support byte-range requests when required for practical video seeking.

If object storage is adopted later, short-lived signed URLs may be used following authorization, provided their expiration, scope, and access implications are acceptable.

Do not expose permanent public URLs for sensitive evidence.

### 7.5 Retention

The retention policy is a product and institutional decision requiring approval.

Until that policy is approved:

- Use only authorized test data.
- Document where uploaded media is stored.
- Avoid automatic deletion behavior that could destroy evidence unexpectedly.
- Provide a clear separation between test fixtures and real uploaded content.

---

## 8. Authentication and Authorization

### 8.1 Authentication Model

Use server-managed sessions for the initial web application.

Recommended behavior:

1. The user submits credentials over HTTPS.
2. The backend verifies the password against a secure password hash.
3. The backend creates a random session token.
4. The database stores a hash of the session token with the associated user and expiration time.
5. The browser receives the session token in a secure cookie.
6. Subsequent requests are authenticated using that cookie.
7. Logout invalidates the corresponding server-side session.

Do not store session tokens or authoritative access credentials in browser local storage.

### 8.2 Session Cookie

For production:

- HttpOnly must be enabled.
- Secure must be enabled over HTTPS.
- Use an appropriate SameSite setting, normally Lax for a same-site application.
- Set an explicit expiration policy.
- Rotate the session after successful authentication and other relevant privilege changes.
- Invalidate sessions on logout and account deactivation.

Use a maintained password-hashing implementation with Argon2id where compatible with the selected authentication library.

### 8.3 CSRF Protection

Because the application uses cookies for authentication, protect state-changing endpoints against cross-site request forgery.

Use a documented CSRF protection mechanism and validate request origins where appropriate.

SameSite cookies are useful but should not be treated as the only security control.

### 8.4 Roles

The initial role set is:

- operator
- supervisor
- technical_admin

Permissions must be checked on the server for every protected action.

| Capability | Operator | Supervisor | Technical administrator |
|---|---|---|---|
| View incidents | Yes | Yes | As authorized |
| View restricted evidence | Yes, if authorized | Yes, if authorized | Only when authorized and necessary |
| Record review outcomes | Yes | Yes | No by default |
| View reliability metrics | Read-only | Yes | Yes |
| Inspect processing errors | No by default | Read-only if permitted | Yes |
| Configure supported sources | No | No by default | Yes |
| Run evaluations | No | No by default | Yes |
| Manage accounts | No | No by default | Only if implemented and approved |
| Change detector configuration | No | No | Within approved scope |

### 8.5 Resource-Level Authorization

Checking a user's role is not always sufficient.

The backend must also verify that the requested incident, evidence record, evaluation, or source is within the user's permitted access scope.

Even though the initial deployment targets one institution, every request for restricted evidence must perform an authorization check.

### 8.6 Demonstration Accounts

For development and demonstrations, a seeding command may create predefined users.

- Do not commit real passwords.
- Do not ship a publicly accessible default administrator account.
- Take passwords from secure environment configuration or a controlled setup prompt.
- Disable unnecessary seed-account creation in production.
- Clearly document demonstration-account limitations.

### 8.7 Multi-Tenancy

Multi-tenant organizational management is excluded from the initial MVP.

Do not add elaborate organization, billing, or tenant-provisioning infrastructure now. Before serving multiple independent institutions, introduce explicit tenant ownership and resource isolation across every relevant entity and query.

---

## 9. API Architecture

### 9.1 API Style

Use a versioned REST API returning JSON for application data.

Base path: **/api/v1**

The API should use:

- Explicit request and response schemas.
- Consistent HTTP status codes.
- Query parameters for filters, sorting, and pagination.
- Standardized error responses.
- OpenAPI documentation for development and testing.

The frontend must use the documented API contract rather than depending on internal database field names.

### 9.2 Main API Endpoints

The following endpoint set defines the recommended MVP contract. Exact request and response schemas must be defined during implementation.

#### Authentication and User Context

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /api/v1/auth/login | Authenticate a user |
| POST | /api/v1/auth/logout | Invalidate the current session |
| GET | /api/v1/auth/me | Return the current user's identity and role |

A CSRF-token endpoint or equivalent mechanism must be included if required by the selected protection strategy.

#### Dashboard

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /api/v1/dashboard/summary | Return summary counts and available operational metrics |

Summary responses must identify the relevant time range and metric source.

#### Incidents

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /api/v1/incidents | List incidents with filtering, sorting, and pagination |
| GET | /api/v1/incidents/{incident_id} | Return an incident and associated metadata |
| GET | /api/v1/incidents/{incident_id}/reviews | Retrieve review records when review history is supported |
| POST | /api/v1/incidents/{incident_id}/reviews | Record a human review outcome |

The list endpoint should support the filters that are actually implemented, including time range, source, category, and review status.

#### Evidence

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /api/v1/evidence/{evidence_id} | Return authorized evidence metadata |
| GET | /api/v1/evidence/{evidence_id}/content | Stream authorized video or image content |

The content endpoint must enforce authorization and protect against access to unrelated files.

#### Reliability and Evaluation

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /api/v1/reliability/summary | Return available reliability metrics |
| GET | /api/v1/evaluations | List authorized evaluation runs |
| POST | /api/v1/evaluations | Create an evaluation job from a supported dataset |
| GET | /api/v1/evaluations/{evaluation_id} | Retrieve evaluation status and results |

A dataset-registration endpoint may be added if required by the chosen evaluation workflow. Do not implement a dataset-upload management interface unless the MVP actually needs it.

#### Sources and Processing

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /api/v1/sources | List configured video or simulated sources |
| GET | /api/v1/sources/{source_id} | Inspect source details |
| GET | /api/v1/system/status | Return processing and system status |
| GET | /api/v1/jobs/{job_id} | Retrieve processing-job status |

Source-creation and configuration endpoints should be limited to source types approved for the MVP.

#### Operational Health

| Endpoint | Purpose |
|---|---|
| /health/live | Indicate whether the application process is running |
| /health/ready | Indicate whether required dependencies are ready for requests |

Health endpoints must not expose credentials, private paths, internal configuration, or sensitive diagnostics.

### 9.3 Pagination

Use bounded pagination on list endpoints.

Responses should provide returned items, page or cursor information, whether additional results exist, and total counts only when available and reasonably inexpensive.

Set a sensible maximum page size. Do not permit unbounded incident retrieval by default.

### 9.4 Filtering and Sorting

- Validate filters using explicit schemas or allowlists.
- Allow only documented sort fields.
- Reject or safely normalize unsupported sorting inputs.
- Never insert user-provided sort strings directly into SQL expressions.
- Keep filter semantics consistent across the frontend and backend.

### 9.5 Review Submission

The review endpoint must:

1. Authenticate the user.
2. Verify review permissions.
3. Validate the requested outcome.
4. Create a review record.
5. Update the incident's current review status when appropriate.
6. Preserve the original detector prediction.
7. Commit the transaction.
8. Return the persisted review and current incident state.

Repeated requests should not accidentally create duplicate records due to routine frontend retries. Use an idempotency key or another appropriate duplicate-submission strategy when necessary.

### 9.6 Error Responses

Use a consistent JSON error format following the Problem Details approach where practical.

A response should identify a machine-readable error code or type, a safe human-readable message, the HTTP status, optional validation detail, and a request identifier for support and debugging.

Do not expose stack traces, SQL details, file-system paths, access tokens, or internal secrets in API responses.

### 9.7 API Documentation

FastAPI can generate OpenAPI documentation.

- Keep interactive API documentation enabled in development.
- Restrict or disable public interactive documentation in production unless there is a deliberate need for it.
- Test important API contracts.
- Ensure all endpoints enforce authorization independently of whether they appear in the frontend.

---

## 10. Data Flow

### 10.1 Incident Detection

1. A prerecorded clip or configured event source is registered.
2. The application validates the source and creates the corresponding processing job.
3. The source is stored or referenced through the storage interface.
4. The job becomes available to the worker.
5. The worker retrieves the source and decodes the media.
6. Video-quality checks run.
7. The detector adapter produces normalized predictions.
8. The reliability module evaluates supported quality and evidence criteria.
9. The application persists incident records, assessments, and evidence references.
10. The worker records job completion or failure.
11. The frontend retrieves the resulting incidents and statuses.

If there is not enough evidence to support interpretation, the system must preserve that uncertainty rather than manufacture a definitive result.

### 10.2 Human Review

1. The operator opens an incident.
2. The API returns the incident, associated evidence metadata, detector output, and reliability assessments the user is allowed to access.
3. The browser requests video or frames through the authorized evidence endpoint.
4. The operator selects a review outcome.
5. The frontend submits the review.
6. The backend validates authorization and input.
7. The backend persists the review and updates the current review status transactionally.
8. The API returns the saved state.
9. The frontend updates or invalidates the relevant cached data.

The model prediction remains unchanged.

### 10.3 Reliability Evaluation

1. An authorized user requests an evaluation.
2. The backend validates the dataset and detector configuration.
3. A processing job is created.
4. The worker evaluates the dataset against reference annotations.
5. The metric service calculates supported metrics.
6. The application records the model version, dataset version, configuration, sample counts, and outcomes.
7. The frontend retrieves the completed result.
8. The reliability dashboard displays metrics with their evaluation context and limitations.

### 10.4 System Status

1. The worker and API record processing outcomes.
2. Source and job records reflect their current states.
3. The status endpoint returns information relevant to the requesting user's permissions.
4. The system-status screen displays current availability and recent failures.

A successful HTTP response must not be interpreted as proof that video inference succeeded. Application health and processing health are separate indicators.

### 10.5 Public Context Enrichment

1. A permitted source has an approved, coarse-grained context area and context retrieval enabled.
2. An authorized refresh request creates a context-enrichment job; it does not include video bytes or personal data.
3. The worker searches public webpages through TinyFish Search, applies source policy, and fetches selected pages through TinyFish Fetch.
4. It validates and normalizes title, source URL/domain, topic, bounded excerpt, publication time when available, and retrieval time.
5. The database stores deduplicated context items linked to the source and job.
6. The API returns only normalized metadata and excerpts; the interface displays source links and freshness state.

Search results are candidate public context, not proof. A provider failure or stale result must be clearly labeled and must not change the detector result, incident review status, or metric calculations.

---

## 11. Background Processing and Job Management

### 11.1 MVP Job Queue

Use PostgreSQL as the source of truth for background job status. The MVP job types are `source_processing`, `evaluation`, and `context_enrichment`; keep each type's input/output contract explicit.

A `context_enrichment` job must reference one authorized source with `context_retrieval_enabled` and a non-empty approved `context_area_label`. It queries public web information only and must not reference or upload evidence bytes. Provider calls and result persistence run in the existing worker. A disabled integration or missing API key should mark the context feature unavailable without affecting incident review or video processing.

A processing job should include:

- Job ID.
- Job type.
- Input or dataset reference.
- Current status.
- Creation and start timestamps.
- Completion timestamp, when available.
- Attempt count.
- Safe error code or summary.
- Relevant output references.

Suggested states:

- pending
- running
- completed
- failed

Additional retry or cancellation states should be introduced only if required by implemented behavior.

### 11.2 Worker Execution

Run one worker process initially.

The worker must:

- Claim pending jobs safely.
- Avoid two workers processing the same job simultaneously if the deployment later scales to multiple workers.
- Mark the job as running.
- Execute the appropriate processing handler.
- Persist outputs.
- Mark the job completed or failed.
- Record safe diagnostics.
- Release or recover abandoned jobs according to a documented rule.

Use short database transactions when claiming jobs and saving results. Do not hold a transaction open throughout lengthy video inference.

### 11.3 Retries

- Retry transient failures when safe.
- Do not retry invalid inputs indefinitely.
- Limit attempts.
- Avoid duplicating incidents or evidence during retries.
- Record the final error.
- Allow an authorized administrator to inspect the result.

### 11.4 Queue Limitations

A database-backed queue is sufficient for a low-volume MVP.

Do not add Redis or a dedicated message broker merely because the system uses background jobs.

Consider a dedicated queue only if measurements establish a need for higher throughput, more advanced scheduling, or stronger delivery guarantees.

### 11.5 Job Recovery

If a worker exits while processing a job, the application must not leave the record silently appearing to be active forever.

The implementation should use a heartbeat, lease, or started-at timeout to identify abandoned work and safely recover or mark it failed.

---

## 12. External Services and Integrations

### 12.1 Required External Services

The application needs:

- The selected deployment environment.
- PostgreSQL.
- A video-storage location appropriate to the deployment.
- Any required model weights or locally provisioned model artifacts.
- TinyFish Search and Fetch for best-effort public-web contextual enrichment when the feature is enabled and configured.

TinyFish is not used for video inference and must never receive media or personal data. The core application must remain usable if contextual retrieval is disabled or unavailable.

### 12.2 TinyFish Public Context Adapter

Use the documented TinyFish REST APIs through the backend HTTP client:

- Search: `GET https://api.search.tinyfish.ai` with `query` and, where useful, `location`, `language`, `include_domains`, `exclude_domains`, `search_type`, and date/freshness filters supported by the current provider contract.
- Fetch: `POST https://api.fetch.tinyfish.ai` with a bounded `urls` list and `format: "markdown"` for clean, readable source content. Fetch accepts at most 10 URLs per request according to the current reference; SafeCity should use a smaller configured limit for its MVP.
- Both services authenticate with the server-side `X-API-Key` header using `TINYFISH_API_KEY`.

The exact provider schema must be checked against the official documentation before implementation. Normalize provider responses into internal typed schemas; do not let provider-specific JSON leak through the public SafeCity API.

#### Retrieval flow

1. An authorized user or configured schedule requests context refresh for a source.
2. The API validates that the source is authorized, enabled for context retrieval, and has an approved area label.
3. The API creates a `context_enrichment` job and returns its job ID.
4. The worker generates narrowly scoped topic/time queries, searches for public pages, and selects bounded candidate URLs using configured policy.
5. The worker validates URL scheme/domain rules and fetches appropriate pages. Private IPs, localhost, cloud metadata endpoints, file URLs, userinfo URLs, and unapproved destinations must never be fetched by the application.
6. The worker extracts a short source-grounded excerpt or concise deterministic summary; it must not invent a fact absent from the fetched page.
7. It stores the context item with the original/final source URL, title, publisher/domain, topic, publication time when available, retrieval time, freshness policy, and safe provider metadata.
8. The frontend shows source attribution, retrieval/publication times, and freshness state. The operator can open the original source to verify it.

#### Reliability and safety rules

- Set explicit connect/read timeouts, a bounded URL count and content length, response-size limits, refresh cooldowns, a per-job time budget, and rate-aware backoff.
- Distinguish no relevant results from provider failure, timeout, malformed output, source fetch failure, and disabled configuration.
- Treat all retrieved text as untrusted content, including text that attempts to issue instructions.
- Prefer official weather authorities, transport operators, and institutional/public-notice domains. A domain allowlist must be configurable and enforced server-side; search results are not automatically trusted.
- Preserve publication time when supplied. When the publisher gives no time, display publication time as unknown rather than inferring it from search-result order.
- A successful provider call does not mean the information is verified, current, or causally related to an incident.
- External context must not modify detector scores, reliability metrics, incident review status, or initiate notification/dispatch.
- TinyFish's Agent/browser API is out of MVP scope; consider it only for a separately approved workflow that genuinely requires multi-step interactions.

### 12.3 Optional Future Integrations

These are not MVP requirements:

- Commercial video-management systems.
- Live RTSP or ONVIF sources.
- Object storage such as an S3-compatible service.
- External identity providers.
- Monitoring and error-reporting services.
- External notification systems.

Every future integration must be reviewed for authentication, data exposure, licensing, and operational necessity.

### 12.4 External AI Services

Do not send real surveillance footage or identifying information to an external AI service by default.

If an external provider is later considered, approval is required for the provider, data-processing terms, retention behavior, security boundaries, and the permitted types of data.

### 12.5 Network Boundaries

- The browser communicates only with the application's public HTTP interface.
- The API and worker communicate with PostgreSQL through private service networking.
- The worker accesses video through the configured storage interface.
- The database must not be publicly exposed.
- Production secrets must not be included in frontend bundles or public repository files.

---

## 13. Environment Configuration

### 13.1 Configuration Strategy

All deployment-specific configuration must be provided through environment variables or an approved secret-management mechanism.

Use a validated configuration module so that missing or malformed critical configuration causes a clear startup error.

Avoid scattering raw environment-variable access throughout the codebase.

### 13.2 Configuration Categories

The implementation will likely require settings for:

**Application**
- Environment name.
- Debug mode.
- Public application origin.
- API prefix.
- Log level.

**Database**
- Database connection URL.
- Connection-pool settings where needed.

**Authentication**
- Session-related secrets where applicable.
- Session lifetime.
- Cookie security settings.
- Password and session policy.

**Storage**
- Local storage root or object-storage configuration.
- Maximum upload size.
- Supported media types.
- Evidence-retention configuration after approval.

**Processing**
- Worker polling interval.
- Maximum job attempts.
- Processing time limits where appropriate.
- Detector implementation and version.
- Quality-check thresholds approved for the deployment.
- TinyFish context feature switch, API key, request timeout, maximum results/URLs per refresh, source-domain allowlist, context cache/freshness TTL, and per-source refresh cooldown.

**Evaluation**
- Dataset storage location.
- Annotation format.
- Event-matching configuration.
- Supported evaluation options.

Only settings required by the chosen implementation should be introduced. This list is not a reason to add configuration for features that are not built.

### 13.3 Secret Management

- Commit .env.example containing placeholder values only.
- Ignore actual .env files and secret-bearing local configuration.
- Do not place API keys, database credentials, session secrets, or passwords in source code.
- Rotate secrets when exposure is suspected.
- Do not expose backend environment variables through the frontend build process.
- Fail safely when critical production secrets are missing.

### 13.4 Environment Separation

Maintain separate configurations for:

- Local development.
- Automated testing.
- Demonstration or staging.
- Production, if deployed.

Do not run destructive tests against demonstration or production data.

---

## 14. Error Handling and Observability

### 14.1 Error Categories

| Category | Examples | Expected behavior |
|---|---|---|
| Validation | Invalid review outcome, malformed event | Reject request and return safe validation details |
| Authentication | Expired or invalid session | Return an authentication error and request login as appropriate |
| Authorization | Restricted evidence requested without permission | Deny access without leaking protected details |
| Missing resource | Unknown incident or evidence ID | Return not found |
| Conflict | Duplicate or incompatible state transition | Return a conflict when applicable |
| Upload | Unsupported, oversized, or malformed media | Reject the file and record a safe error |
| Processing | Decode or inference failure | Mark the job failed and retain diagnostic information |
| Storage | Evidence unavailable | Mark evidence unavailable and keep other incident information usable |
| Database | Query or transaction failure | Roll back and return a safe error |
| Service unavailable | Required database or storage dependency unavailable | Report degraded availability appropriately |

### 14.2 User-Facing Errors

Users should see concise, actionable error messages.

Do not expose raw stack traces, SQL statements, filesystem paths, secrets, internal networking details, model artifacts, or private file locations.

An ordinary operator needs to know what failed and whether the incident can still be reviewed. A technical administrator may receive additional diagnostic information when authorized.

### 14.3 Structured Logging

Use structured logs for:

- Application errors.
- Request identifiers.
- Processing-job lifecycle events.
- Authentication failures.
- Review-save failures.
- Storage and decoding failures.
- Evaluation-run completion and failure.

Avoid logging passwords, session tokens, full video contents, unnecessary personal information, or sensitive payloads.

### 14.4 Request and Job Correlation

Assign a request identifier to incoming API requests.

Processing jobs must have stable job identifiers. Where a job originates from a request, retain a safe correlation reference so administrators can trace failures from a UI operation to the corresponding processing record.

### 14.5 Metrics and Monitoring

The MVP needs basic operational visibility, not a complete observability platform.

Track or expose where feasible:

- API error counts.
- Processing-job counts by status.
- Job duration.
- Failed video-processing attempts.
- Database availability.
- Evaluation-run completion and failure.

Do not make application monitoring depend on the detector or video-processing pipeline being monitored.

### 14.6 Health Checks

- Liveness should indicate whether the application process can run.
- Readiness should verify the dependencies needed to serve the configured functionality.
- Worker health should be monitored independently from HTTP liveness.
- Expensive inference jobs should not run as part of routine health checks.

---

## 15. Security Boundaries

### 15.1 Trust Boundaries

Treat all of the following as untrusted until validated:

- Browser-submitted data.
- Uploaded files.
- Detector outputs.
- External source metadata.
- Dataset annotations.
- Media filenames.
- Query parameters.
- Stored evidence references supplied by clients.

Validate each input at the relevant boundary.

### 15.2 Video Upload Security

Where upload functionality is implemented:

- Enforce a configured maximum size.
- Allow only supported media formats.
- Do not trust file extensions or browser-provided content types alone.
- Validate that the file can be decoded.
- Generate internal storage names.
- Prevent path traversal.
- Keep uploaded files out of public static directories.
- Restrict access to uploaded media.
- Apply appropriate processing time and resource limits.
- Treat malformed files as processing failures, not incidents.

### 15.3 API Security

- Authenticate protected requests.
- Enforce role and resource authorization server-side.
- Validate every request using explicit schemas.
- Restrict CORS to known development or production origins where cross-origin development requires it.
- Use HTTPS in production.
- Apply appropriate request-size limits.
- Rate-limit authentication and other exposed, abuse-prone operations where appropriate.
- Keep API documentation private or disabled in production unless intentionally exposed.
- Return safe error responses.

### 15.4 Database Security

- Use a database account with only the permissions required by the application.
- Keep the database on private networking.
- Require authenticated connections between application processes and the database.
- Do not expose database credentials to the browser.
- Back up the database according to the deployment's data requirements.
- Test recovery procedures before relying on backups.
- Use migrations for schema evolution.

### 15.5 Evidence Security

- Authenticate and authorize every evidence request.
- Ensure an evidence ID cannot be used to access another user's restricted evidence.
- Keep private media outside public static assets.
- Avoid permanent public links.
- Restrict administrative access to evidence.
- Do not log the contents of video or extracted frames.
- Apply an approved retention and deletion policy when one is established.

### 15.6 Security and Product Safety

The product must not implement excluded capabilities such as facial recognition, cross-camera identity tracking, individual criminality scoring, or autonomous punitive actions.

A detector event is a candidate for human review, not proof of criminal intent.

### 15.7 Auditability

At minimum, review records must preserve the reviewer, outcome, and timestamp.

If review history or broader audit logging is implemented, protect it against ordinary users altering or deleting historical decisions without authorization.

Do not claim a tamper-proof audit system unless an appropriate technical design and verification process exist.

---

## 16. Testing Strategy

Testing should focus on the core workflow and failure cases rather than merely maximizing coverage percentages.

### 16.1 Backend Unit Tests

Test:

- Incident normalization.
- Source-event deduplication.
- Quality-check calculations.
- Uncertainty decisions.
- Event-matching rules.
- Precision and recall calculations.
- False-alert-rate calculations.
- Detection-delay calculations.
- Review-state transitions.
- Configuration validation.
- Storage-path validation.
- TinyFish response normalization, URL policy checks, and context freshness calculations.

Use small deterministic input data with independently calculated expected results.

### 16.2 API Tests

Test:

- Login and logout.
- Current-user resolution.
- Role-based access.
- Incident listing and filtering.
- Incident details.
- Evidence access restrictions.
- Review submission and persistence.
- Processing-job status.
- Evaluation creation and retrieval.
- Validation and error responses.
- Session expiration and invalidation.
- Context listing and refresh authorization, including source-level context enablement.
- Provider errors and stale context represented through the documented contract.

Include unauthorized requests that bypass the frontend and call protected endpoints directly.

### 16.3 Database Integration Tests

Use a real test PostgreSQL instance for tests involving:

- Constraints.
- Transactions.
- Foreign keys.
- Duplicate prevention.
- Review persistence.
- Job claiming.
- Concurrent access where supported.
- Database migrations.

Do not rely exclusively on in-memory substitutes for tests of PostgreSQL-specific behavior.

### 16.4 Frontend Tests

Test:

- Navigation.
- Incident filtering.
- Incident-detail rendering.
- Loading and empty states.
- Missing-evidence handling.
- Reliability warnings.
- Review selection and submission.
- API failures and retries.
- Accessible labels and keyboard interactions.
- Responsive critical controls where practical.

### 16.5 AI and Evaluation Tests

Use a deterministic test dataset with known reference labels.

Test:

- Video-decoding failures.
- Invalid or incomplete detector outputs.
- Quality-check behavior.
- Prediction normalization.
- Ground-truth matching.
- Metric values.
- Zero denominators.
- Missed events.
- Excluded samples.
- Evaluation-version tracking.
- Context-enrichment job retry, idempotent ingestion, duplicate elimination, provider timeout, and missing publication-time handling.
- A test proving public context cannot create an incident, change detector outputs, or overwrite a review.

A simulated detector may be used to test the workflow, but its results must not be represented as real model performance.

### 16.6 End-to-End Tests

At minimum, verify the primary journey:

1. Sign in as an authorized user.
2. Open an incident.
3. Inspect evidence or the expected unavailable-evidence state.
4. Inspect reliability information.
5. Record a review.
6. Verify that the review persists.
7. Verify that the original detector prediction remains unchanged.
8. Open the reliability dashboard and verify the available evaluation data.

Also test the processing-failure path and verify that a failed video does not create an unsupported confirmed incident.

### 16.7 Test Data

- Keep sample media small and appropriately licensed.
- Do not commit private surveillance footage.
- Use synthetic fixtures when possible.
- Clearly label demonstration events.
- Keep test expectations reproducible.
- Do not use fabricated benchmark results as acceptance evidence.

### 16.8 CI Requirements

A pull request should run the relevant automated checks:

- Formatting and linting.
- Type checking.
- Frontend tests.
- Backend tests.
- API and integration tests as configured.
- Production builds.
- Migration checks where practical.

Deploy only after the required checks pass.

---

## 17. Repository Structure

The following is the recommended logical structure. Adapt it to the existing repository rather than duplicating directories or introducing folders with no actual responsibility.

    safecity/
    ├── frontend/
    │   ├── src/
    │   │   ├── app/
    │   │   │   ├── router/
    │   │   │   └── providers/
    │   │   ├── components/
    │   │   │   ├── layout/
    │   │   │   ├── ui/
    │   │   │   └── feedback/
    │   │   ├── features/
    │   │   │   ├── overview/
    │   │   │   ├── incidents/
    │   │   │   ├── reliability/
    │   │   │   ├── sources/
    │   │   │   └── evaluations/
    │   │   ├── lib/
    │   │   │   ├── api/
    │   │   │   └── types/
    │   │   ├── styles/
    │   │   │   └── tokens.css
    │   │   ├── main.tsx
    │   │   └── ...
    │   ├── tests/
    │   ├── package.json
    │   └── ...
    │
    ├── backend/
    │   ├── app/
    │   │   ├── api/
    │   │   │   └── v1/
    │   │   │       ├── auth.py
    │   │   │       ├── dashboard.py
    │   │   │       ├── incidents.py
    │   │   │       ├── evidence.py
    │   │   │       ├── reliability.py
    │   │   │       ├── evaluations.py
    │   │   │       ├── sources.py
    │   │   │       └── system.py
    │   │   ├── core/
    │   │   │   ├── config.py
    │   │   │   ├── security.py
    │   │   │   └── errors.py
    │   │   ├── db/
    │   │   │   ├── session.py
    │   │   │   └── models.py
    │   │   ├── schemas/
    │   │   ├── repositories/
    │   │   ├── services/
    │   │   ├── adapters/
    │   │   │   ├── detectors/
    │   │   │   └── storage/
    │   │   ├── processing/
    │   │   │   ├── jobs.py
    │   │   │   ├── worker.py
    │   │   │   └── video.py
    │   │   ├── evaluation/
    │   │   │   ├── matching.py
    │   │   │   └── metrics.py
    │   │   └── main.py
    │   ├── migrations/
    │   ├── tests/
    │   │   ├── unit/
    │   │   ├── api/
    │   │   └── integration/
    │   ├── pyproject.toml
    │   └── ...
    │
    ├── scripts/
    │   ├── seed_demo_users.py
    │   └── ...
    ├── docs/
    ├── .env.example
    ├── .gitignore
    ├── Dockerfile
    ├── compose.yaml
    ├── PRD.md
    ├── DESIGN.md
    ├── ARCHITECTURE.md
    └── README.md

### 17.1 Folder Rules

- API modules contain routing, input/output schemas, and calls into services.
- Services contain business workflows and validation belonging to application logic.
- Repositories contain persistence queries.
- Adapters contain integrations with model implementations and file storage.
- Processing contains job execution and video-processing coordination.
- Evaluation contains matching and metric logic.
- Shared frontend components must not import feature-specific business logic.
- Keep the repository structure proportional to actual functionality; do not create empty modules for possible future features.

---

## 18. Local Development

### 18.1 Environment

Use a reproducible local environment with:

- Frontend development server.
- FastAPI development server.
- PostgreSQL.
- One background worker.
- Local video storage for permitted test assets.

Docker Compose is the recommended default for PostgreSQL and the backend worker. The frontend may run through Vite during development.

### 18.2 Startup Sequence

The development setup should:

1. Load and validate environment configuration.
2. Start PostgreSQL.
3. Apply approved database migrations.
4. Start the FastAPI application.
5. Start the background worker.
6. Start the frontend development server.
7. Verify application and processing health.

Provide one documented workflow for installing dependencies, applying migrations, seeding authorized demo users, and starting the application.

### 18.3 Local CORS

If the frontend and backend run on different development origins, configure CORS for the exact development origins and required credentials.

Do not use unrestricted CORS in production.

In production, prefer serving the frontend and API through the same public origin to simplify cookie handling and security configuration.

### 18.4 Local Assets

Keep uploaded videos, model weights, temporary frame extracts, and local database files outside the frontend's publicly served assets.

Add generated or sensitive data directories to .gitignore.

---

## 19. Deployment Approach

### 19.1 MVP Deployment

Use a simple deployment with:

- One web application service.
- One worker process or service using the same application image.
- One PostgreSQL database.
- A durable video-storage location.
- HTTPS at the public boundary.

The web service handles HTTP requests. The worker processes queued video and evaluation jobs. Both use the same backend code and shared database schema.

### 19.2 Frontend Delivery

Build the React application into static assets.

Serve those assets through the same public origin as the API, using a straightforward static-file server or reverse proxy.

API requests should remain under /api/v1. Do not introduce separate public domains unless the deployment requires them.

### 19.3 Database Deployment

Use a managed or otherwise properly maintained PostgreSQL deployment for a shared demonstration or production environment.

- Restrict public access.
- Configure backups.
- Apply schema migrations deliberately.
- Monitor connection limits.
- Document database restoration procedures.

### 19.4 Video Storage Deployment

Local filesystem storage is acceptable during development and in an MVP deployment with a durable attached volume and a single application deployment.

If that durability or sharing guarantee is unavailable, use a suitable private object-storage service before accepting real video data.

The application must not assume that ephemeral container storage survives redeployment.

### 19.5 Worker Deployment

Run one worker initially.

The deployment must ensure that:

- It can access PostgreSQL.
- It can access video storage.
- It uses the expected model configuration and files.
- It can restart safely after failure.
- Its job status is visible to the API.
- A worker restart does not corrupt completed records.

### 19.6 Deployment Safety

- Keep production secrets in deployment configuration or a secret manager.
- Run migrations as a controlled deployment step.
- Do not reset the production database during startup.
- Verify API readiness before routing traffic.
- Confirm worker health separately.
- Keep uploaded media out of ephemeral paths.
- Ensure logs do not contain private evidence or credentials.

### 19.7 Rollback

A rollback procedure should cover application version rollback and database compatibility.

Use backward-compatible migrations where possible. Do not assume that rolling back application code also reverses a schema migration safely.

---

## 20. MVP Architecture Versus Future Scalability

### 20.1 Build Now

The initial implementation should include:

- One React frontend.
- One FastAPI modular monolith.
- One PostgreSQL database.
- One detector adapter.
- One background worker.
- Local or private durable evidence storage.
- Role-based access control.
- Session-based authentication.
- An evidence-review workflow.
- Reliability and evaluation modules.
- Structured logging and essential health checks.
- Automated tests for critical workflows.

### 20.2 Defer Until Needed

Do not implement these without a demonstrated requirement:

- Microservices.
- Kubernetes.
- Redis or Kafka.
- Dedicated distributed task queues.
- Multiple model-serving services.
- Multi-tenant organization management.
- Complex event streaming.
- Distributed caching.
- Automated model retraining.
- Multi-region deployment.
- Advanced analytics infrastructure.
- Real-time multi-camera orchestration.
- External notification and dispatch integrations.

### 20.3 Scale-Up Triggers

| Current limitation | Potential future change | Trigger |
|---|---|---|
| One worker cannot keep up with job volume | Add workers with safe concurrency control | Measured queue backlog and processing delay |
| Database-backed job claiming becomes a bottleneck | Introduce a dedicated queue | Demonstrated throughput or scheduling requirements |
| Local media storage cannot support shared access | Adopt private object storage | Multiple application instances or storage durability requirements |
| API response times degrade under load | Optimize queries, indexes, and connection pooling | Measured latency and database profiling |
| One institution is no longer sufficient | Introduce tenant-aware data access | Approved multi-institution product requirement |
| Inference slows down interactive API operations | Separate model inference into a dedicated service | Measured resource contention or scaling needs |
| More operational visibility is required | Add external metrics, tracing, or error reporting | Production support requirements |
| Evaluation workloads compete with operational reviews | Isolate evaluation execution or allocate dedicated workers | Measured processing contention |

The first response to a performance problem should be measurement and targeted optimization, not automatic infrastructure expansion.

---

## 21. Architectural Decisions and Approval Requirements

### 21.1 Proposed Defaults

| Decision | Recommended default | Rationale |
|---|---|---|
| Backend architecture | FastAPI modular monolith | Simple ownership and deployment |
| Frontend | React with TypeScript and Vite | Component-based interface and straightforward static build |
| Database | PostgreSQL | Durable relational state and transactional integrity |
| ORM and migrations | SQLAlchemy and Alembic | Explicit database interaction and schema evolution |
| Video-processing runtime | Python with OpenCV where applicable | Compatibility with video and ML libraries |
| Job management | PostgreSQL-backed queue with one worker | Avoids a separate message broker for the MVP |
| Authentication | Server-managed sessions in secure cookies | Keeps long-lived credentials out of browser storage |
| Evidence storage | Storage adapter with local development implementation | Keeps storage choices separate from the product workflow |
| Frontend styling | CSS variables and CSS Modules | Direct implementation of DESIGN.md tokens |
| API contract | Versioned REST JSON API | Straightforward frontend integration and testing |
| Deployment | Web service, worker, PostgreSQL, durable storage | Small operational footprint |

### 21.2 Decisions That Still Require Approval

The coding agent must not silently finalize:

1. The actual detection model and model-weight source.
2. The initial event categories supported by that model.
3. The evaluation dataset and annotation provenance.
4. The video-quality checks and their thresholds.
5. The evidence-sufficiency and abstention policy.
6. The retention policy and permitted video sources.
7. The target hosting provider.
8. Whether live CCTV integration is required for the first version.
9. Whether object storage is necessary for the selected deployment.
10. The approved performance and reliability targets.

Where a choice does not affect safety, data integrity, or product scope, the coding agent may use the recommended default and document the decision.

---

## 22. Implementation Order

Implementation should proceed in increments that preserve an end-to-end working product.

### Phase 1 — Foundation

- Inspect and preserve the repository's existing work.
- Establish the frontend, backend, and shared configuration.
- Configure PostgreSQL and migrations.
- Implement authentication and role resolution.
- Implement basic health checks.
- Establish the shared API client and design tokens.

### Phase 2 — Incident Workflow

- Define the normalized incident schema.
- Implement incident ingestion and deduplication.
- Implement evidence metadata and storage references.
- Build the incident list and detail screens.
- Add quality-assessment and uncertainty fields.
- Implement human review persistence.
- Add critical authorization and data-integrity tests.

### Phase 3 — Video Processing

- Select the approved video input.
- Implement the storage adapter.
- Implement the selected detector or explicitly labeled simulated feed.
- Implement the background job lifecycle.
- Add supported video-quality checks.
- Validate evidence association and failure handling.

### Phase 4 — Reliability Evaluation

- Define dataset and annotation formats.
- Implement event matching and metric calculations.
- Persist evaluation runs and results.
- Build the reliability dashboard.
- Validate calculations against independently prepared expected results.

### Phase 5 — Integration and Delivery

- Complete loading, empty, error, and uncertainty states.
- Run end-to-end tests.
- Verify keyboard access and responsive layouts.
- Verify that all demo data is clearly identified.
- Configure a reproducible deployment.
- Document operational setup, model provisioning, and known limitations.

This order is a dependency sequence, not a fixed deadline. Do not postpone basic error handling, access control, or data integrity until the end.

---

## 23. Architecture Acceptance Criteria

The architecture is implemented satisfactorily when:

- [ ] The frontend communicates with the backend through documented API contracts.
- [ ] The backend is organized as a modular monolith.
- [ ] Database access is isolated from HTTP route handlers.
- [ ] PostgreSQL stores authoritative incident and review state.
- [ ] Original detector predictions remain distinct from reliability assessments and reviewer outcomes.
- [ ] Video files are stored outside public frontend assets.
- [ ] Evidence requests enforce authentication and authorization.
- [ ] Long-running video processing is handled through background jobs.
- [ ] A processing failure cannot silently become a confirmed incident.
- [ ] Job retries do not create duplicate incidents or evidence records.
- [ ] Evaluation metrics are traceable to versioned inputs and documented matching rules.
- [ ] Undefined metrics are represented as unavailable.
- [ ] Session handling and CSRF protection are implemented appropriately.
- [ ] Sensitive configuration is kept out of source control and frontend bundles.
- [ ] Database migrations and automated tests are part of the development workflow.
- [ ] The application and worker can be monitored independently.
- [ ] The MVP runs without unnecessary microservices or infrastructure.
- [ ] Simulated data is never represented as genuine model output or live CCTV.
- [ ] All implementation decisions that affect model behavior, evidence policy, or deployment assumptions are documented.

---

## 24. Final Architecture Definition

SafeCity AI should be built as a React and TypeScript web application backed by a Python FastAPI modular monolith, PostgreSQL, and a small background worker for video processing and evaluation.

The architecture's central boundary is the normalized incident workflow. Detector-specific behavior, video-quality assessment, evidence storage, human review, and metric calculation remain separate responsibilities connected through explicit data models and service interfaces.

The first deployment should support one institution, one selected detection pipeline, authorized prerecorded or simulated inputs, secure evidence access, human-reviewed outcomes, and reproducible metric evaluation.

Further infrastructure should be introduced only when measured requirements justify it.

**The defining architectural principle is simple: keep the application small, preserve the evidence and decision history, and make every reliability claim traceable to actual data.**
