# SafeCity AI — Product Requirements Document

**Version:** 1.0  
**Status:** Draft — pending approval of key assumptions  
**Product type:** Reliability-aware public-space incident intelligence platform  
**Primary customers:** Universities, private campuses, facility-management companies, and security-system integrators  
**Primary business model:** B2B institutional subscriptions

---

## 1. Product Overview

### 1.1 Product Summary

SafeCity AI is an AI-powered incident intelligence platform that helps authorized security operators review potentially significant events detected in surveillance video.

The product focuses on making video-analysis alerts more reliable, explainable, and operationally useful. It does not aim to replace existing CCTV infrastructure or build another general-purpose surveillance analytics platform.

SafeCity AI introduces a reliability-aware layer around incident detection. It evaluates available video quality, associates alerts with supporting evidence, communicates uncertainty when evidence is insufficient, and measures system performance against labeled evaluation data.

Human operators remain responsible for reviewing alerts and making consequential decisions.

### 1.2 Problem Statement

Surveillance analytics can detect objects, track movement, and flag potentially anomalous activity. However, an automated detection does not necessarily establish that a meaningful incident occurred.

Security teams may face several challenges:

- **Scene-dependent performance:** Camera placement, image quality, lighting, occlusion, and differences between environments can affect detection reliability.
- **False alerts:** Harmless activities can trigger alerts, consuming operator time.
- **Weak evidence presentation:** An alert may provide a score without clearly showing the observations that caused it.
- **Insufficient uncertainty handling:** Poor visibility or incomplete evidence may prevent reliable interpretation.
- **Limited performance visibility:** Security teams need measurable information about false alerts, missed incidents, detection delay, and review workload.

These are risks to investigate and measure, not assumptions that all existing surveillance products fail in these ways.

### 1.3 Value Proposition

SafeCity AI aims to help institutions:

1. Review alerts using relevant video evidence and supporting observations.
2. Identify video conditions that may undermine detection reliability.
3. Communicate uncertainty instead of presenting weak evidence as a definitive conclusion.
4. Reduce unnecessary alert-review workload without materially increasing missed incidents.
5. Evaluate system performance using documented, measurable metrics.

**Core value proposition:** Help security teams distinguish actionable alerts from unreliable detections while making the reasoning and limitations behind each alert easier to inspect.

### 1.4 Product Differentiation

SafeCity AI's initial differentiation is not the invention of another incident detector. It is the combination of:

- Video-quality assessment.
- Evidence-associated alerts.
- Explicit uncertainty and abstention.
- Human review.
- Quantitative reliability evaluation.

The product must demonstrate measurable value against an appropriate baseline before claiming superiority over established vendors or research models.

---

## 2. Goals and Non-Goals

### 2.1 Product Goals

- Ingest candidate incident detections from a supported video-analysis pipeline.
- Present alerts and relevant evidence in a centralized interface.
- Assess video quality and evidence sufficiency.
- Communicate uncertainty and processing failures clearly.
- Allow authorized operators to record review outcomes.
- Calculate reliability metrics against labeled evaluation data.
- Identify performance differences across supported video conditions.
- Enrich source-level situational awareness with attributed public context—such as official weather advisories, transport disruptions, and public notices—retrieved through TinyFish Search and Fetch.
- Provide a credible demonstration of reduced nuisance-alert workload without unacceptable loss of detection performance.

### 2.2 Non-Goals

The MVP will not:

- Replace existing CCTV infrastructure.
- Build a complete video-management system.
- Perform facial recognition or identify individuals.
- Track individuals across unrelated cameras.
- Predict an individual's likelihood of committing a crime.
- Automatically accuse, punish, or classify individuals as criminals.
- Automatically dispatch emergency services.
- Guarantee incident detection or prevention.
- Eliminate human review.
- Claim production-grade performance without appropriate testing.

---

## 3. Target Users and Customers

### 3.1 User Personas

| User | Primary needs | Key activities |
|---|---|---|
| Security operator | Review alerts efficiently and understand available evidence | Inspect alerts, review clips, record outcomes |
| Security supervisor | Understand incident patterns and alert reliability | Monitor performance, review outcomes, assess workload |
| Technical administrator | Keep configured sources and processing operational | Inspect source status, investigate errors, manage supported configuration |
| Institutional decision-maker | Understand operational value and system limitations | Evaluate aggregate performance and determine whether to adopt the product |

### 3.2 Initial Customer Segments

- Universities and university campuses.
- Private institutional campuses.
- Facility-management companies.
- Security-system integrators.

### 3.3 Initial Deployment Assumptions

- **A1:** The first version will target a single institution.
- **A2:** The initial interface will be a desktop-oriented web application.
- **A3:** The MVP may use prerecorded clips or a simulated event feed instead of live CCTV.
- **A4:** The system will initially integrate one detection pipeline.
- **A5:** Operators will review alerts before any consequential action is taken.

These assumptions require confirmation before the affected implementation decisions are finalized.

---

## 4. Core User Journeys

### 4.1 Journey A — Review an Incident

1. An authorized operator signs in.
2. The operator views the incident dashboard.
3. The operator selects an alert.
4. The incident detail screen displays the event timestamp, source, detection category, available scores, and reliability warnings.
5. The operator inspects the associated video clip, frames, or other evidence.
6. The operator reviews any quality or uncertainty warnings.
7. The operator records a review outcome.
8. The system persists the outcome and updates the incident's review status.

**Expected result:** The operator can distinguish a model-generated prediction from a human-reviewed outcome.

### 4.2 Journey B — Handle an Uncertain Detection

1. A candidate event is received.
2. The system detects that video quality or evidence sufficiency does not meet the configured requirements.
3. The system records the uncertainty status and its available reason.
4. The interface communicates that the alert cannot be reliably interpreted from the available evidence.
5. The operator reviews the available information and records an outcome.

**Expected result:** Poor-quality or insufficient evidence does not automatically become a confirmed incident.

### 4.3 Journey C — Evaluate Reliability

1. A supervisor opens the reliability dashboard.
2. The supervisor selects or inspects an evaluation period.
3. The system displays the available metrics and sample counts.
4. The supervisor reviews false alerts per hour, precision, recall, detection delay, and review time where calculable.
5. The supervisor examines supported condition-specific results.
6. The supervisor uses the findings to identify reliability problems requiring investigation.

**Expected result:** Performance claims are traceable to a dataset, evaluation period, and documented metric definitions.

### 4.4 Journey D — Investigate a Processing Problem

1. A technical administrator opens system status.
2. The administrator inspects the configured video source and processing state.
3. The system displays recent processing failures.
4. The administrator inspects the available diagnostic information.
5. The administrator corrects the supported configuration or retries processing when appropriate.

**Expected result:** Processing failures are visible and do not silently produce misleading incident records.

### 4.5 Journey E — Run a Benchmark Evaluation

1. An authorized evaluator selects a labeled dataset.
2. The configured detection pipeline processes eligible clips.
3. Predictions are compared with independently established reference labels.
4. The system calculates the supported evaluation metrics.
5. The evaluator inspects results and processing failures.

**Expected result:** The team can assess system performance without relying on fabricated or hardcoded metrics.

### 4.6 Journey F — Review Public Context

1. An authorized user opens a configured source with an approved public context area.
2. The system retrieves candidate public information through TinyFish Search and, where suitable, Fetch.
3. The system stores bounded excerpts with the original URL, publisher when available, publication time when available, and retrieval time.
4. The interface shows the item as contextual information with its freshness and provenance, separate from video detections and reliability scores.
5. The operator opens the source to verify context if it is useful.

**Expected result:** Public information can help an operator understand the surrounding situation, but it cannot confirm or disprove a video incident or trigger consequential action.

---

## 5. User Stories

| ID | User story | Priority |
|---|---|---|
| US-01 | As an operator, I want to see recent alerts so that I can identify events requiring review. | P0 |
| US-02 | As an operator, I want to inspect evidence associated with an alert so that I can assess the detection. | P0 |
| US-03 | As an operator, I want to see quality and uncertainty warnings so that I do not mistake weak evidence for certainty. | P0 |
| US-04 | As an operator, I want to record whether an alert was confirmed, false, or inconclusive. | P0 |
| US-05 | As a supervisor, I want to see reliability metrics so that I can evaluate alert quality and review workload. | P0 |
| US-06 | As a supervisor, I want to understand the evaluation period and sample size so that I can interpret metrics correctly. | P0 |
| US-07 | As a technical administrator, I want to see processing failures so that I can investigate operational problems. | P0 |
| US-08 | As an evaluator, I want to compare predictions with labeled events so that I can measure detection performance. | P0 |
| US-09 | As an evaluator, I want to compare performance across video conditions so that I can identify reliability gaps. | P1 |
| US-10 | As a supervisor, I want to compare detector versions so that I can determine whether a change improves reliability. | P1 |
| US-11 | As an operator, I want to filter alerts by time, source, category, and review status so that I can find relevant incidents quickly. | P0 |
| US-12 | As an administrator, I want access to restricted functionality to depend on my role so that incident data remains protected. | P0 |

Priority definitions: **P0** is required for the MVP; **P1** should be implemented if time and infrastructure permit.

---

## 6. Functional Requirements

### 6.1 Authentication and Authorization

**FR-001 — Controlled access (P0)**  
The application must restrict access to authorized users. A simplified authenticated environment is acceptable for a local demonstration if implemented safely.

**FR-002 — Role-based permissions (P0)**  
The application must distinguish operators, supervisors, and technical administrators.

**FR-003 — Authorization enforcement (P0)**  
Permissions must be enforced by the application or backend data-access layer, not only by hiding interface controls.

### 6.2 Incident Ingestion

**FR-004 — Receive candidate detections (P0)**  
The application must receive detection events from the configured detector, evaluation pipeline, or simulated feed.

**FR-005 — Normalize event data (P0)**  
Incoming detections must be converted into a consistent internal incident representation.

**FR-006 — Validate event data (P0)**  
Malformed events must be rejected or recorded as processing failures without generating misleading incident conclusions.

**FR-007 — Handle duplicate events (P0)**  
Repeated delivery of an event with a stable identifier must not create duplicate incident records.

**FR-008 — Track processing status (P0)**  
The application must distinguish pending, successful, and failed processing.

### 6.3 Video Quality and Uncertainty

**FR-009 — Video-quality assessment (P0)**  
The system must assess a feasible subset of video-quality characteristics, such as blur or sharpness, brightness or exposure, resolution, frame availability and decoding failures, and obstruction or insufficient visible scene information where reliably measurable. Only checks supported by the chosen pipeline must be implemented.

**FR-010 — Store assessment results (P0)**  
The system must associate available quality-assessment results with the relevant incident or video segment.

**FR-011 — Evidence sufficiency (P0)**  
The system must represent whether available evidence is sufficient for the configured assessment process.

**FR-012 — Uncertainty and abstention (P0)**  
The system must support an uncertain or abstained outcome when configured checks indicate that a reliable interpretation cannot be supported.

**FR-013 — Explain uncertainty (P0)**  
Where possible, the interface must display the reason for an uncertainty or quality warning.

**FR-014 — Preserve score semantics (P0)**  
Detector confidence, anomaly score, video quality, and evidence sufficiency must remain distinct concepts. The system must not present one as a substitute for another.

**FR-015 — Avoid unsupported conclusions (P0)**  
Missing data, poor video quality, or processing failures must not be treated as proof that an incident occurred.

### 6.4 Evidence Management

**FR-016 — Associate evidence with alerts (P0)**  
An alert must reference available supporting evidence, such as video clips, extracted frames, relevant timestamps, source identifiers, detection category and score, and reliability-assessment results.

**FR-017 — Report missing evidence (P0)**  
The interface must explicitly indicate when evidence is missing, inaccessible, or could not be processed.

**FR-018 — Maintain evidence integrity (P0)**  
Evidence must be associated with the correct incident and must not be silently substituted with unrelated footage.

**FR-019 — Evidence-grounded explanations (P0)**  
Any explanation must be supported by available observations. The system must not invent actions, motives, identities, or events.

**FR-020 — Restrict evidence access (P0)**  
Restricted video evidence must only be accessible to authorized users.

### 6.5 Incident Review

**FR-021 — Incident list (P0)**  
The interface must display available alerts with their timestamp, source, detection category, review status, and reliability warning when available.

**FR-022 — Incident detail (P0)**  
Users must be able to inspect an incident's metadata, evidence, and reliability information.

**FR-023 — Filtering and sorting (P0)**  
Users must be able to filter or sort incidents by supported attributes, including time, source, category, and review status.

**FR-024 — Review outcomes (P0)**  
An authorized operator must be able to record one of the following outcomes: confirmed by reviewer, false alert, or inconclusive/insufficient evidence.

**FR-025 — Preserve original predictions (P0)**  
Human review outcomes must not overwrite the original model-generated result.

**FR-026 — Review notes (P1)**  
The system may support optional operator notes.

**FR-027 — Review history (P1)**  
The system may preserve a history of review changes, timestamps, and reviewer identifiers.

### 6.6 Reliability Evaluation

**FR-028 — Calculate reliability metrics (P0)**  
The system must support calculation of false alerts per hour, precision, recall, detection delay, and review time if sufficient data is available.

**FR-029 — Use documented definitions (P0)**  
Each metric must follow the definitions in Section 11.

**FR-030 — Evaluate against labeled data (P0)**  
The system must compare detector outputs with independently established reference labels.

**FR-031 — Report evaluation metadata (P0)**  
Each evaluation must identify its dataset, evaluation period, model or detector version, and sample counts.

**FR-032 — Break down results by condition (P1)**  
Where suitable labels and sufficient samples exist, results should be available by supported conditions such as lighting, image quality, occlusion, or camera.

**FR-033 — Compare evaluation runs (P1)**  
The system should support comparison of different model versions or configurations.

**FR-034 — Distinguish metric sources (P0)**  
The interface must distinguish benchmark results from operational metrics based on human-reviewed incidents.

### 6.7 System Status

**FR-035 — Display source status (P0)**  
The system must display whether the configured input source and processing pipeline are available, processing, or experiencing an error.

**FR-036 — Report processing failures (P0)**  
Processing failures must be visible to authorized administrators.

**FR-037 — Identify demo mode (P0)**  
The interface must explicitly identify simulated or prerecorded data and must not imply that live CCTV is connected when it is not.

### 6.8 Public Context Enrichment (TinyFish)

**FR-038 — Retrieve public context (P0)**  
For a source with context retrieval enabled and an approved area label, the backend must be able to use TinyFish Search to find public context relevant to a bounded time window and supported topics. The integration must use public pages only.

**FR-039 — Fetch and attribute sources (P0)**  
Where feasible, the backend must use TinyFish Fetch to retrieve selected source pages and preserve source title, publisher/domain, canonical or final URL, publication time when available, and retrieval time.

**FR-040 — Preserve provenance and freshness (P0)**  
Every displayed context item must show its source and retrieval time, plus publication time or a clear “not provided” state. Stale, unknown-age, partial, and unavailable results must be distinguishable.

**FR-041 — Keep context separate (P0)**  
External context must remain separate from detector predictions, video-quality assessments, reliability metrics, and human review outcomes. It must not create, suppress, confirm, or reclassify a video incident by itself.

**FR-042 — Bound retrieval (P0)**  
Context queries must use a configured area, allowlisted topics, bounded result counts, request timeouts, rate controls, and a documented freshness window. Refresh work must be asynchronous and deduplicated where possible.

**FR-043 — Degrade safely (P0)**  
TinyFish timeouts, rate limits, invalid responses, empty results, and disabled configuration must not block incident review, evidence playback, or video processing. The UI must report context unavailable rather than presenting an empty result as verified safety.

**FR-044 — Protect data and credentials (P0)**  
Only approved public search queries and public URLs may be sent to TinyFish. Surveillance footage, frames, evidence bytes, credentials, private URLs, and personal data must not be sent to the provider. The API key must remain server-side.

---

## 7. Non-Functional Requirements

### 7.1 Performance

**Proposed targets — pending approval:**

| Operation | Initial target |
|---|---|
| Load dashboard data | Within 3 seconds at the 95th percentile |
| Load incident metadata | Within 2 seconds at the 95th percentile, excluding video buffering |
| Save a review outcome | Within 2 seconds at the 95th percentile |
| Load precomputed reliability metrics | Within 3 seconds at the 95th percentile |

These targets apply to application interactions under a defined test environment. Video-inference speed and end-to-end detection latency must be measured separately.

### 7.2 Reliability

- Processing failures must not be silently discarded.
- Duplicate event delivery must be handled safely where identifiers permit.
- Missing evidence must be visible.
- Model predictions must remain distinguishable from human conclusions.
- Unavailable metrics must not be displayed as zero.
- Partial data availability must not make the entire application unusable.

### 7.3 Security

- Protected functionality must require appropriate authorization.
- Secrets and credentials must not be exposed in client-side code or logs.
- Uploaded files must be validated before processing.
- Restricted video evidence must not be publicly accessible by default.
- Error messages must not reveal secrets or sensitive implementation details.

### 7.4 Privacy

- Initial testing should use synthetic, appropriately licensed public, consented, or otherwise authorized video.
- Facial recognition and identity-based tracking are excluded.
- Personal data collection must be limited to what is necessary.
- Video retention must follow an approved policy.
- Restricted evidence must be available only to authorized personnel.
- Video must not be used to train unrelated models without explicit authorization.

**Approval required:** Confirm the video-retention period, data permissions, and institutional privacy requirements before processing real campus footage.

### 7.5 Explainability

- Alerts should identify their source and available supporting observations.
- Reliability warnings should explain their reason where possible.
- Scores must be labeled according to their actual meaning.
- An anomaly score must not be described as a probability of criminal activity without independent validation.
- The interface must not present a model prediction as ground truth.

### 7.6 Maintainability

- Keep incident ingestion, reliability assessment, evidence handling, review management, and metric calculation logically separated.
- Avoid coupling the interface to a single detector implementation.
- Document event schemas and metric definitions.
- Record model versions for evaluations.
- Prefer simple architecture over unnecessary services or infrastructure.

### 7.7 Accessibility and Usability

- Use consistent terminology and clear status labels.
- Do not communicate critical warnings through color alone.
- Maintain readable text and sufficient contrast.
- Support standard desktop and laptop screen sizes.
- Ensure operators can understand alerts without specialist machine-learning knowledge.

---

## 8. Pages and Screens

### 8.1 Login

**Purpose:** Provide controlled access.

**Required elements:** Application name; authentication form or approved demonstration login; validation and error messages.

**States:** Default, submitting, invalid credentials, authentication unavailable.

### 8.2 Operations Dashboard

**Purpose:** Summarize alert activity and processing status.

**Required elements:** Recent alerts; counts by review status; high-level reliability metrics when available; processing and source status; supported filters.

**Requirements:** Clearly identify the time period for summary counts; mark unavailable metrics as unavailable; label prerecorded or simulated data.

### 8.3 Incident List

**Purpose:** Locate and prioritize alerts.

**Required elements:** Timestamp; source or camera identifier; detection category; review status; reliability indicator; filtering and sorting controls.

### 8.4 Incident Detail

**Purpose:** Inspect an alert and record a review.

**Required elements:** Incident metadata; relevant clip or extracted frames when available; detection result and score; video-quality assessment; evidence-sufficiency and uncertainty status; supporting observations when available; review-outcome controls.

**Requirements:** Distinguish predictions from human review; show unavailable evidence explicitly; enforce evidence-access permissions.

### 8.5 Reliability Dashboard

**Purpose:** Evaluate alert quality and operational performance.

**Required elements:** Evaluation period; data source and sample counts; false alerts per hour; precision and recall; detection delay; review time if measurable; supported condition-specific results.

**Requirements:** Use documented metric definitions; display evaluation timestamps and model versions; identify insufficient-data conditions; distinguish benchmark results from operational estimates.

### 8.6 System Status and Sources

**Purpose:** Inspect configured sources and processing health.

**Required elements:** Source identifier and type; processing status; last successful processing time when available; recent processing errors; configuration controls for supported sources.

For an MVP using prerecorded clips, this screen should represent the clip source and processing pipeline rather than implying full CCTV management.

### 8.7 Evaluation Results

**Purpose:** Inspect benchmark outputs.

**Required elements:** Dataset identifier and version; model or detector version; evaluation status and timestamp; sample counts; metric outputs; processing failures; supported condition-specific breakdowns.

This screen may be integrated into the reliability dashboard if a separate page is unnecessary.

---

## 9. Roles and Permissions

| Capability | Operator | Supervisor | Technical administrator |
|---|---|---|---|
| View incident list | Yes | Yes | Yes, as needed |
| View authorized evidence | Yes | Yes | Only when authorized and necessary |
| Record review outcomes | Yes | Yes | No by default |
| View reliability metrics | Read-only | Yes | Yes |
| Inspect processing errors | No by default | Read-only if permitted | Yes |
| Configure supported sources | No | No by default | Yes |
| Run evaluations | No | No by default | Yes |
| Manage users | No | No by default | If implemented |
| Change detector configuration | No | No | Within approved scope |

**Assumption:** The MVP may use predefined demonstration accounts instead of a complete user-management workflow.

All permissions must be enforced by the relevant application authorization layer.

---

## 10. Data Requirements

### 10.1 Incident

Each incident must support:

- Unique incident ID.
- Source event ID, when provided.
- Source or camera ID.
- Event timestamp, when provided.
- Ingestion timestamp.
- Detection category.
- Original detector score and its documented meaning, when available.
- Detector/model version, when available.
- Processing status.
- Associated reliability assessment.
- Evidence references.
- Human review status.
- Creation timestamp.

### 10.2 Reliability Assessment

Each assessment must support:

- Assessment ID.
- Associated incident or video segment.
- Assessment timestamp.
- Computed video-quality measurements.
- Quality-check results.
- Evidence-sufficiency status.
- Uncertainty or abstention status.
- Machine-readable reason codes.
- Human-readable explanation based on available results.
- Assessment version.

Only measurements that were actually computed may be stored as measured values.

### 10.3 Evidence

Each evidence record must support:

- Evidence ID.
- Associated incident ID.
- Evidence type.
- Storage reference.
- Relevant timestamps, when applicable.
- Creation timestamp.
- Processing status.
- Availability status.
- Optional integrity checksum.

Video content should be stored separately from ordinary incident metadata where practical.

### 10.4 Human Review

Each review record must support:

- Review ID.
- Incident ID.
- Reviewer ID.
- Review outcome.
- Review timestamp.
- Optional note.
- Optional review-change history.

Human outcomes must not overwrite original detector outputs.

### 10.5 Evaluation Dataset

The evaluation dataset must support references to:

- Dataset ID and version.
- Video or clip IDs.
- Ground-truth event labels.
- Event start and end times, where available.
- Source or scene labels, where available.
- Video-condition labels, where available.
- Annotation provenance.
- Data usage permissions.

Ground-truth labels must be independently established and must not be inferred from the model being evaluated.

### 10.6 Evaluation Run

Each run must record:

- Evaluation run ID.
- Dataset ID and version.
- Model or detector version.
- Configuration and thresholds.
- Start and completion timestamps.
- Evaluation status.
- Sample counts.
- Metric outputs.
- Exclusions and failure counts.

### 10.7 Data Integrity

- IDs must be unique within their entity types.
- Timestamps must have a consistent format and timezone interpretation.
- Missing values must remain distinguishable from zero.
- Review outcomes must remain separate from model predictions.
- Evidence must reference the correct incident.
- Metric outputs must be traceable to the dataset and evaluation run that produced them.

---

## 11. Metric Definitions

### 11.1 False Alerts per Hour

The number of false-positive alerts divided by the eligible monitored-video duration in hours. False detections representing the same underlying event must be handled according to a documented event-merging rule.

### 11.2 Precision

Precision measures the proportion of qualifying detections that match ground-truth events.

**Precision = TP / (TP + FP)**

Where TP is true positives and FP is false positives. The metric is unavailable when the denominator is zero.

### 11.3 Recall

Recall measures the proportion of ground-truth events detected by the system.

**Recall = TP / (TP + FN)**

Where FN is false negatives.

### 11.4 Detection Delay

The elapsed time between the ground-truth event onset and the first qualifying detection. The event-matching window and treatment of missed events must be documented.

### 11.5 Review Time

The time spent reviewing an alert, measured through a defined interaction or annotation procedure. Report the chosen summary statistic and sample count. If reliable review-duration data is unavailable, mark the metric unavailable.

### 11.6 Condition-Specific Performance

Where data permits, evaluate performance separately across conditions such as lighting, image quality, occlusion, and camera or scene. Each breakdown must show sample counts and must not imply strong conclusions from insufficient data.

### 11.7 Undefined Metrics

Metrics that cannot be calculated because of missing data or zero denominators must be marked unavailable, not set to zero.

---

## 12. Integrations

### 12.1 Video-Analysis Pipeline

The application must consume candidate detections from one configured pipeline. Potential sources include a research anomaly-detection model, a supported event-detection model, or a simulated event generator.

**Important:** UCF-Crime is a research dataset and benchmark context, not a complete production surveillance service. The actual model implementation and its supported inputs must be selected before integration.

### 12.2 Video Input

At least one input method must be supported for the MVP:

- Prerecorded video clips.
- A controlled simulated event feed.

Live CCTV integration using RTSP, ONVIF, or a vendor-specific interface is optional and requires approval.

### 12.3 Evidence Storage

The application must maintain valid references to evidence accessible to authorized application components. Local or application-managed storage is acceptable for a controlled demonstration.

### 12.4 Database

The application must persist incident metadata, reliability assessments, review outcomes, evaluation metadata, and processing status. The database technology is not predetermined. The coding agent should use the simplest suitable option compatible with the existing project.

### 12.5 Frontend and Backend

The application interface must support retrieving incidents and details, retrieving evidence and reliability assessments, saving review outcomes, retrieving processing status, and retrieving evaluation metrics. Existing repository conventions should be reused where practical.

### 12.6 TinyFish Public Context Integration

TinyFish is the MVP's provider for best-effort public-web contextual enrichment; it is not the video detector or a source of ground truth.

- Use the TinyFish Search API to discover public pages relevant to an explicitly configured source area, topic, and time window: `GET https://api.search.tinyfish.ai`.
- Use the TinyFish Fetch API to retrieve bounded page content from selected public URLs: `POST https://api.fetch.tinyfish.ai`.
- Authenticate server-side with the `X-API-Key` header from `TINYFISH_API_KEY`.
- Keep provider calls behind a backend adapter and run refresh work through the background worker.
- Prefer official weather, transport, institutional, and public-notice sources. Preserve attribution and timing metadata and provide a link for operator verification.
- Validate returned URLs and content, limit results and excerpts, deduplicate items, and label stale or unknown-age information. Treat page text as untrusted input.
- Do not submit video, frames, private footage URLs, personal data, credentials, or internal-only information to TinyFish.
- TinyFish outages must not interrupt incident review or inference. The context feature must be safely disabled when its key or approved configuration is absent.
- Do not use the Agent/browser API in the MVP unless a later, specific requirement justifies multi-step site interaction and is separately approved.

### 12.7 Excluded External Integrations

The MVP does not include emergency-service dispatch, external messaging or notification services, facial-recognition APIs, commercial video-management integrations, enterprise identity-provider integrations, or general-purpose external inference on surveillance footage.

---

## 13. Loading, Empty, Error, and Uncertainty States

### 13.1 Dashboard

- **Loading:** Display a loading indicator while data is retrieved.
- **Empty:** Explain that no alerts are available for the selected period.
- **No matching results:** Explain that active filters produced no results and allow clearing filters.
- **Error:** Explain that dashboard data could not be retrieved and offer retry when appropriate.
- **Unavailable metrics:** Clearly label metrics that cannot be calculated.

### 13.2 Incident List

- **Loading:** Display a loading indicator or placeholders.
- **Empty:** Distinguish between no incidents existing and no incidents matching filters.
- **Error:** Display a clear failure message and retry action.
- **Partial data:** Show available metadata while identifying missing fields or evidence.

### 13.3 Incident Detail

- **Loading:** Allow incident metadata to load independently from video evidence where practical.
- **Missing evidence:** State that evidence is unavailable or was not generated.
- **Unsupported media:** Explain that the evidence format cannot be displayed.
- **Processing failure:** Display the failure state and a diagnostic reference for authorized users.
- **Uncertain detection:** Explain the uncertainty and avoid presenting a definitive incident conclusion.
- **Access denied:** Do not expose restricted evidence or sensitive metadata.

### 13.4 Reliability Dashboard

- **Loading:** Indicate when metrics are being retrieved or calculated.
- **No evaluation data:** Explain why metrics are unavailable.
- **Insufficient sample size:** Qualify or withhold the affected metric.
- **Calculation failure:** Identify the metric as unavailable and provide retry when appropriate.
- **Stale results:** Display the evaluation timestamp and identify results that do not reflect the latest completed evaluation.

### 13.5 System Status

- **Loading:** Display the status-retrieval state.
- **No configured sources:** Explain that no sources are configured and provide supported setup instructions.
- **Source unavailable:** Show the source as unavailable.
- **Invalid configuration:** Identify the validation problem without exposing secrets.
- **Simulated mode:** Explicitly label prerecorded or simulated input.

### 13.6 Evaluation

- **Loading:** Display processing status and progress when available.
- **No eligible videos:** Explain that no videos qualify for the evaluation.
- **Partial failure:** Report successful and failed samples separately.
- **Completed:** Display metrics, dataset details, detector version, and timestamp.
- **Failed:** Display a failure state and an appropriate diagnostic reference.

---

## 14. MVP Scope

### 14.1 Must Have

- Controlled application access.
- Role-aware permissions.
- One detector pipeline or simulated detection source.
- Incident ingestion and normalization.
- Incident list and detail screens.
- Evidence association.
- Basic video-quality assessment.
- Explicit uncertainty and evidence-insufficiency handling.
- Human review outcomes.
- Persistence of incident and review records.
- Reliability metric calculation on a labeled dataset.
- Processing status and error visibility.
- Public context retrieval through TinyFish Search/Fetch for sources with an approved area and context enabled, including provenance, freshness states, and graceful degradation.
- Appropriate loading, empty, and error states.
- A reproducible end-to-end demonstration.

### 14.2 Should Have

- Condition-specific evaluation breakdowns.
- Review notes and review history.
- Comparison of detector configurations.
- More detailed source-management functionality.

### 14.3 Out of Scope

- Full live CCTV integration.
- Multi-site enterprise deployment.
- Multiple simultaneous detectors.
- Automated model retraining.
- Advanced scene calibration.
- Complex reporting and exports.
- Automated notifications.
- Mobile applications.
- Facial recognition and cross-camera identity tracking.
- Individual risk scoring.
- Automated accusations or punitive actions.
- Autonomous emergency-service dispatch.

---

## 15. Success Criteria

The MVP will be considered successful when:

1. A user can open an incident and inspect its associated evidence.
2. Available quality assessments and uncertainty warnings are displayed correctly.
3. An authorized operator can record and retrieve a review outcome.
4. The application preserves the original prediction separately from human review.
5. The system calculates false alerts per hour, precision, recall, and other supported metrics correctly on a known evaluation dataset.
6. Processing errors and missing evidence are visible.
7. Access restrictions are enforced.
8. The end-to-end demonstration works without falsely implying a live-camera connection.
9. The evaluation methodology documents the dataset, matching rules, and relevant limitations.
10. Any claimed reduction in review workload or false alerts is supported by a baseline comparison.
11. Public context is attributed to its source, displays retrieval/publication timing when available, and cannot create, suppress, or reclassify a video incident.

**No fixed percentage improvement is assumed.** A target reduction in false alerts or review time must be approved after the baseline, dataset, and evaluation methodology are established.

---

## 16. Acceptance Tests

### AT-01 — Incident Ingestion

Given a valid detection event, when it is submitted, the system creates or updates the appropriate incident record and makes it available in the incident list.

### AT-02 — Duplicate Handling

Given the same identifiable source event is submitted repeatedly, the application does not create duplicate incident records.

### AT-03 — Evidence Association

Given an incident with associated evidence, an authorized operator can inspect the correct evidence and timestamps.

### AT-04 — Missing Evidence

Given an incident without accessible evidence, the application explicitly indicates that the evidence is unavailable.

### AT-05 — Quality Warning

Given a video that fails a configured quality check, the system records the result and displays the corresponding warning.

### AT-06 — Uncertainty Handling

Given an event that fails the configured evidence-sufficiency criteria, the system can mark the result as uncertain without presenting it as confirmed.

### AT-07 — Review Persistence

Given an unreviewed incident, an authorized operator can record a review outcome and retrieve it after reopening the incident.

### AT-08 — Prediction and Review Separation

Given a model prediction and a human review outcome, the application displays both distinctly and preserves the original prediction.

### AT-09 — Metric Correctness

Given a labeled evaluation dataset with independently calculated reference results, the system produces matching metrics under the same event-matching rules.

### AT-10 — Insufficient Data

Given an evaluation in which a metric cannot be calculated, the system marks it unavailable or appropriately qualified rather than displaying a misleading zero.

### AT-11 — Access Control

Given a user without permission to view restricted evidence, a direct request for that evidence is denied by the relevant authorization layer.

### AT-12 — Processing Failure

Given an invalid or unreadable video file, the system records the processing failure and does not infer a positive incident conclusion from that failure.

### AT-13 — Demo Integrity

Given a deployment using simulated or prerecorded data, the interface identifies the data mode and does not claim to be connected to live CCTV.

### AT-14 — TinyFish Context Provenance and Failure Isolation

Given a source with context retrieval enabled, returned public context displays the original source URL and retrieval time, preserves publication time when supplied, and is shown separately from detections and review outcomes. Given a TinyFish timeout, rate limit, malformed response, or empty result, video processing and incident review remain usable and the context state is reported accurately.

### AT-15 — TinyFish Data Boundary

Given a context-refresh request, only the approved area/topic query and allowlisted public URLs may be sent to TinyFish; video bytes, extracted frames, credentials, private URLs, and personal data are never included.

---

## 17. Assumptions and Decisions Requiring Approval

### 17.1 Assumptions

| ID | Assumption | Impact |
|---|---|---|
| A1 | Prerecorded or simulated input is acceptable for the first demo | Live CCTV is not mandatory |
| A2 | Initial deployment serves one institution | Multi-tenant architecture is unnecessary |
| A3 | Desktop web interface is sufficient | Native mobile applications are excluded |
| A4 | One detector pipeline is sufficient | Multiple integrations can be deferred |
| A5 | A suitable labeled dataset can be obtained or prepared | Quantitative evaluation is possible |
| A6 | Evidence can be stored using application-managed references | Vendor-specific storage is not mandatory |
| A7 | Operators review alerts before consequential action | Automated consequential actions are excluded |
| A8 | Simplified demonstration authentication is acceptable | Full user-management workflows can be deferred |

### 17.2 Decisions Requiring Approval

- **D1 — Input mode:** Prerecorded clips, simulated feed, or live CCTV.
- **D2 — Detection pipeline:** Actual detector/model implementation and supported event categories.
- **D3 — Incident categories:** Event types credible enough to include in the MVP.
- **D4 — Quality checks:** Video-quality characteristics to implement.
- **D5 — Uncertainty policy:** Evidence-sufficiency rules, thresholds, and abstention behaviour.
- **D6 — Evaluation dataset:** Dataset selection, permissions, ground-truth annotations, and event-matching rules.
- **D7 — Technology stack:** Frontend, backend, database, model framework, video-processing libraries, and hosting.
- **D8 — Privacy and retention:** Video-retention period, permissions, and institutional requirements.
- **D9 — Authentication:** Full authentication or controlled demonstration access.
- **D10 — Performance:** Approved application response-time targets and separate video-processing targets.
- **D11 — Reliability targets:** Acceptable false-alert rates and maximum acceptable degradation in recall, established through evaluation.
- **D12 — Deployment:** Local demonstration, on-premises deployment, or cloud hosting.
- **D13 — Context source policy:** Approve source-area granularity, initial public context topics, allowed domains where needed, freshness windows, and retention of retrieved excerpts before enabling context retrieval for real operations.

The coding agent must not silently treat these decisions as finalized.

---

## 18. Implementation Instructions for the Coding Agent

1. Inspect the existing repository, dependencies, and current functionality before selecting or changing the architecture.
2. Identify which PRD requirements are already implemented and which remain outstanding.
3. Confirm the necessary decisions before implementing features that depend on them.
4. Build the smallest complete workflow first: ingest detection, create incident, associate evidence, assess reliability, record review, and calculate evaluation metrics.
5. Keep detector-specific code separate from the core application workflow.
6. Implement only quality checks and uncertainty rules supported by the chosen data and model.
7. Validate incoming events and use explicit data schemas.
8. Preserve predictions, evidence, reliability assessments, and human review as distinct records.
9. Use actual metric calculations; never hardcode fabricated evaluation results.
10. Label demo data, prerecorded video, and simulated system status clearly.
11. Implement loading, empty, error, and insufficient-data states.
12. Test critical behaviour, especially ingestion, evidence association, review persistence, metric correctness, and access control.
13. Avoid unnecessary microservices, distributed infrastructure, databases, and orchestration.
14. Do not implement excluded identity-based surveillance or automated punitive actions.
15. When a dependency is unavailable, document the limitation and provide a transparent, testable fallback if appropriate.
16. Keep TinyFish retrieval server-side, asynchronous, bounded, and optional per source; never send surveillance media or personal data to it.
17. Update this PRD when an explicitly approved product decision changes the specification.

## 19. Definition of Done

The MVP is complete when all P0 requirements are implemented or explicitly documented as blocked by an unresolved approval or unavailable dependency; the primary operator workflow functions end to end; reliability metrics are validated against independently calculated results; missing evidence and uncertainty are handled correctly; access restrictions are enforced; critical acceptance tests pass; the demo accurately represents the capabilities and limitations of the implementation; and no unsupported performance or production-readiness claims are presented.

## 20. Final Product Definition

SafeCity AI is a reliability-aware incident intelligence platform that connects candidate detections with video-quality assessment, supporting evidence, uncertainty handling, human review, and measurable evaluation.

Its MVP must demonstrate three capabilities:

1. **Evidence:** Operators can inspect why an alert was generated and what information supports it.
2. **Reliability:** The system can identify insufficient evidence and communicate uncertainty.
3. **Measurement:** The team can quantify false alerts, precision, recall, detection delay, and review workload through a documented evaluation process.

The product's commercial value depends on demonstrating that it reduces unnecessary review effort without materially increasing missed incidents. This must be established through testing against a defined baseline, not assumed from the presence of AI or reliability indicators.
