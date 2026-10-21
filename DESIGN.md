# SafeCity AI — Design System & UX Specification

**Document:** DESIGN.md  
**Version:** 1.0  
**Status:** Initial specification  
**Product:** SafeCity AI  
**Applies to:** All web application screens and reusable interface components  
**Source of truth:** `PRD.md`

---

## 1. Design Vision

### 1.1 Product Experience

SafeCity AI is a reliability-aware public-space incident intelligence platform for security operators, supervisors, and technical administrators.

The interface must help users answer three questions quickly:

1. **What needs attention?** — Identify new, unresolved, and potentially significant alerts.
2. **What evidence supports it?** — Inspect the relevant video, observations, and reliability warnings.
3. **How reliable is the system?** — Understand detector performance, uncertainty, and operational workload.

The visual language should feel like a purpose-built operational tool for reviewing evidence, not a generic SaaS dashboard, an AI chatbot, or a cinematic surveillance interface.

### 1.2 Visual Direction: Evidence-First Operations

The interface uses a restrained, light, high-contrast visual system with compact operational layouts, strong typographic hierarchy, precise tabular data, and carefully controlled status colors.

Its identity comes from how information is presented rather than decorative branding.

**Design characteristics:**

- Neutral surfaces that keep attention on incident evidence.
- Dark, readable typography for important information.
- A restrained blue accent for navigation and primary actions.
- Amber for uncertainty and warnings.
- Red for confirmed critical states or failures that need attention.
- Structured data tables rather than oversized dashboard cards.
- Clear separation between machine-generated detections and human review outcomes.
- Video evidence presented as the focal point of incident investigation.
- Consistent timestamps, source identifiers, and status labels.
- Minimal motion and no decorative visualizations without operational value.

### 1.3 What the Interface Must Not Become

Avoid:

- Neon gradients, glowing borders, and futuristic surveillance motifs.
- Large gradient hero sections or oversized marketing-style headings inside the application.
- Excessive rounded cards, pill-shaped controls, and floating panels.
- An arbitrary grid of KPI cards occupying most of the screen.
- Decorative charts without defined metrics or sufficient data.
- Green success indicators for every ordinary state.
- Red warning badges used for all incident types.
- Unexplained confidence percentages.
- AI-generated summaries presented as authoritative facts.
- Fake live-camera feeds, simulated activity presented as real, or invented performance metrics.
- Excessive animations, glassmorphism, and ornamental icons.

The application is an operational workspace. Information density is acceptable when it improves scanning, but visual clutter is not.

---

## 2. Design Principles

### 2.1 Evidence Before Interpretation

Evidence should be visually prominent in the incident-review workflow.

A video frame, relevant timestamp, or documented observation should be easier to inspect than an explanatory paragraph or a model score.

When evidence is missing, the interface must communicate that limitation directly.

### 2.2 Separate Detection from Human Judgment

The interface must consistently distinguish:

- What the detector reported.
- What the reliability layer assessed.
- What the human reviewer concluded.

These must never appear as interchangeable statuses.

Use explicit labels such as **Model detection**, **Reliability assessment**, and **Reviewer outcome**.

### 2.3 Communicate Uncertainty Honestly

Uncertainty must remain visible without making every uncertain event look like an emergency.

The interface should state what is uncertain and why, when the reason is known.

Examples include:

- Insufficient visual evidence.
- Low video quality.
- Clip unavailable.
- Detection could not be evaluated.
- Human review inconclusive.

An unavailable result is different from a failed result. An uncertain result is different from a false alert.

### 2.4 Optimize for Rapid Scanning

Operators should be able to scan an incident list without opening every record.

Use predictable column positions, consistent timestamps, restrained status labels, and readable metadata.

Important information must not depend exclusively on color.

### 2.5 Make Every Metric Traceable

Charts and quantitative indicators must include enough context to be interpreted correctly.

Show the evaluation period, data source, and sample count where relevant. Where a metric is unavailable, state that explicitly instead of substituting zero.

### 2.6 Keep the Interface Predictable

Shared components must behave consistently across the dashboard, incident list, incident detail, reliability dashboard, and evaluation views.

Use the same typography, spacing, interaction patterns, and status vocabulary throughout.

### 2.7 Minimize Unnecessary Interaction

Common workflows should require as few steps as practical.

Opening an incident, inspecting its evidence, recording a review outcome, and returning to the list should be straightforward.

Do not introduce nested menus, elaborate command palettes, or multiple settings layers unless the implemented functionality requires them.

---

## 3. Color System

### 3.1 Color Strategy

The default theme is light.

Most of the interface should use white and cool-neutral surfaces. Color is reserved primarily for navigation, interaction, and meaningful operational states.

Video imagery supplies much of the interface's natural visual complexity. The surrounding UI must remain restrained so that footage, evidence annotations, and incident details remain legible.

### 3.2 Core Palette

| Token | Hex value | Usage |
|---|---|---|
| Primary background | `#F4F6F8` | Overall application canvas |
| Surface | `#FFFFFF` | Main content surfaces and panels |
| Subtle surface | `#F8FAFC` | Secondary sections and table headers |
| Hover surface | `#F1F5F9` | Hovered rows and interactive items |
| Primary text | `#17212F` | Headings, important values, primary content |
| Secondary text | `#526173` | Supporting information and descriptions |
| Muted text | `#697789` | Timestamps and lower-priority metadata |
| Border | `#D8E0E8` | Standard panel and control borders |
| Strong border | `#BAC6D3` | Emphasized boundaries and selected elements |
| Primary accent | `#2457C5` | Primary actions, active navigation, links |
| Primary accent hover | `#1D46A3` | Hover state for primary actions |
| Primary accent subtle | `#EAF0FF` | Selected navigation and subtle accent backgrounds |
| Focus indicator | `#2457C5` | Keyboard focus outlines |

### 3.3 Semantic Colors

Semantic colors must communicate an actual operational meaning.

| Token | Hex value | Meaning |
|---|---|---|
| Success text | `#17663A` | Completed operation or validated successful state |
| Success background | `#E9F6EE` | Supporting success surface |
| Warning text | `#8A4B08` | Uncertainty, degraded quality, or warning |
| Warning background | `#FFF3D9` | Supporting warning surface |
| Critical text | `#B4232F` | Confirmed critical state or serious failure |
| Critical background | `#FDECEE` | Supporting critical surface |
| Informational text | `#2457C5` | Informational status |
| Informational background | `#EAF0FF` | Supporting informational surface |
| Neutral status text | `#526173` | Pending, inactive, or unclassified state |
| Neutral status background | `#EEF2F6` | Supporting neutral surface |

### 3.4 Status Color Rules

Color must not assign a severity that the underlying data does not support.

- **Unreviewed:** Neutral.
- **Under review:** Blue or neutral.
- **Uncertain detection:** Amber.
- **Low video quality:** Amber.
- **Evidence unavailable:** Neutral or amber, depending on the operational context.
- **False alert, as determined by the reviewer:** Neutral informational treatment.
- **Confirmed by reviewer:** Neutral or informational treatment by default.
- **Confirmed critical incident:** Red only when the reviewed event has a documented critical classification.
- **Processing failure:** Red when the failure requires intervention; otherwise neutral or amber.
- **Successful processing:** Green where a success indicator adds useful information.
- **Unavailable metric:** Neutral.
- **Insufficient evaluation data:** Amber when it materially limits interpretation.

A model-generated anomaly must not receive a red severity treatment merely because the detector produced a high score.

### 3.5 Color Usage Restrictions

- Do not use color as the sole indicator of status.
- Pair status colors with text labels and, where useful, an icon.
- Avoid large colored backgrounds for ordinary table rows.
- Reserve solid semantic backgrounds for compact status labels or clearly bounded warnings.
- Do not use green, amber, and red as generic chart colors without a defined interpretation.
- Keep primary blue reserved for interaction and informational emphasis rather than incident severity.

---

## 4. Typography

### 4.1 Typeface

Use **Inter** as the preferred application typeface, with a system sans-serif fallback when unavailable.

The typography should feel contemporary, precise, and highly legible. Avoid decorative display fonts, condensed fonts for body content, or monospaced typography across the entire interface.

Use tabular numerals for timestamps, metric values, IDs, and other data that benefits from column alignment.

### 4.2 Type Scale

| Level | Size | Weight | Usage |
|---|---:|---|---|
| Page title | 26 px | 650–700 | Main page heading |
| Section heading | 18 px | 600 | Major content sections |
| Subsection heading | 15 px | 600 | Panels and grouped content |
| Body | 14 px | 400 | Main interface content |
| Body emphasis | 14 px | 500–600 | Important descriptions and labels |
| Supporting text | 13 px | 400 | Secondary descriptions and table details |
| Metadata | 12 px | 400–500 | Timestamps, identifiers, supplementary information |
| Metric value | 26–32 px | 600 | Important quantitative values |
| Table header | 12 px | 600 | Column headings, preferably sentence case |

The page-title scale should be used sparingly. Most operational information should remain at 13–15 px for efficient scanning.

Avoid introducing additional font sizes for individual screens when an existing level is sufficient.

### 4.3 Line Height

- Page and section headings: 1.25–1.35.
- Body text: 1.45–1.6.
- Table rows: vertically centered with adequate padding.
- Metadata: 1.4 or greater where practical.

Multi-line descriptions must remain readable without creating unnecessarily tall panels.

### 4.4 Typographic Rules

- Use sentence case for navigation, controls, and headings.
- Use bold sparingly to establish hierarchy.
- Use secondary text color instead of reducing text size excessively.
- Render timestamps and metric values consistently across pages.
- Preserve full incident IDs in detail views, even when shorter representations are shown in lists.
- Use monospaced text only when an identifier, diagnostic value, or technical detail benefits from it.
- Avoid long blocks of uppercase text.

---

## 5. Spacing and Layout System

### 5.1 Base Grid

Use a **4 px spacing unit**.

| Token | Value | Typical usage |
|---|---:|---|
| Space 1 | 4 px | Icon-to-label spacing and tiny internal gaps |
| Space 2 | 8 px | Compact component spacing |
| Space 3 | 12 px | Related controls and metadata |
| Space 4 | 16 px | Standard component padding |
| Space 5 | 20 px | Compact section spacing |
| Space 6 | 24 px | Standard section spacing |
| Space 8 | 32 px | Major content separation |
| Space 10 | 40 px | Large layout gaps |
| Space 12 | 48 px | Major section separation |

Use existing tokens rather than introducing arbitrary spacing values throughout the application.

### 5.2 Application Shell

The desktop application uses three consistent structural areas:

1. **Sidebar:** Primary product navigation.
2. **Top bar:** Page context and account or environment controls.
3. **Main workspace:** Page-specific content.

Recommended desktop dimensions:

- Sidebar width: 224 px.
- Collapsed sidebar width, if implemented: 64 px.
- Top bar height: 56 px.
- Main content horizontal padding: 24 px.
- Main content vertical padding: 24 px.
- Standard panel padding: 16–20 px.
- Panel separation: 16–24 px.

These are starting specifications. Slight adjustments are acceptable when needed to maintain a practical video-review layout.

### 5.3 Content Width

- Operational tables may use the full available workspace width.
- Incident detail screens should use the available desktop width to preserve usable video dimensions.
- Forms and narrow administrative sections should have a readable maximum width rather than stretching across the entire page.
- Text-heavy explanations should not span unnecessarily wide lines.
- Dashboard sections should align to a consistent page grid.

### 5.4 Surfaces and Borders

Use subtle boundaries rather than layers of decorative cards.

- Standard panel background: white.
- Standard panel border: 1 px neutral border.
- Default panel radius: 8 px.
- Inputs and buttons: 6 px radius.
- Compact status labels: 4–6 px radius.
- Large video and evidence surfaces: 6–8 px radius.

Avoid excessive pill-shaped elements and deeply nested card layouts.

Shadows should be rare. Use a restrained shadow only when a menu, dialog, or overlay must be visually separated from underlying content.

### 5.5 Density

The product needs more information density than a consumer application, but not at the expense of readability.

Use compact lists, aligned metadata, and efficient panel layouts. Do not shrink text to fit more data. Prefer pagination or sensible filtering when a dataset is too large.

---

## 6. Application Navigation

### 6.1 Primary Navigation

The sidebar should contain only the core application destinations defined by the PRD.

1. **Overview** — Operational dashboard.
2. **Incidents** — Incident list and review workflow.
3. **Reliability** — Performance metrics and condition-specific evaluation.
4. **System Status** — Configured sources and processing health.

Evaluation results may appear within Reliability rather than creating a separate navigation item unless the implementation requires a distinct evaluation workflow.

### 6.2 Navigation Behavior

- Use a consistent icon and label for each primary destination.
- The active destination must be visually identifiable through a subtle accent background and a clear text treatment.
- Hover and keyboard-focus states must be distinct from active selection.
- Keep the sidebar position and navigation order stable across pages.
- Preserve the current page context when opening a record.
- Use breadcrumbs only where they clarify a multi-level hierarchy, particularly the path from incident list to incident detail.
- Do not add navigation items for unfinished, unavailable, or out-of-scope features.

### 6.3 Top Bar

The top bar should provide only useful global context.

Recommended contents:

- Current page title or compact page context.
- Optional environment indicator such as **DEMO**.
- Current user identity or role menu, if authentication is implemented.

The environment indicator must appear whenever simulated or prerecorded data could otherwise be mistaken for live CCTV.

Avoid unnecessary global search, notification bells, command menus, and other controls unless they correspond to implemented product functionality.

### 6.4 Navigation on Smaller Screens

On narrow screens, the sidebar may collapse into a menu or drawer.

- The current page must remain identifiable.
- The navigation drawer must close after a destination is selected.
- Keyboard focus must remain controlled when the drawer opens and closes.
- Essential incident actions must not be hidden in a hover-only interface.

---

## 7. Reusable Components

All pages must use a shared component system. A component should have one consistent appearance and behavior unless a documented variant is required.

### 7.1 Buttons

#### Primary Button

Use for the main action in a workflow, such as submitting a review outcome.

- Primary accent background.
- White label.
- Clear hover, focus, active, and disabled states.
- One dominant primary action per local workflow where practical.

#### Secondary Button

Use for supporting actions.

- White or neutral background.
- Neutral border.
- Primary text color.

#### Destructive Button

Use only for genuinely destructive operations. Red styling must not be used for ordinary review outcomes or because an event sounds serious.

#### Text Button

Use for low-emphasis actions such as a clear-filter action or opening secondary details.

**Button rules:**

- Standard height: 36 px.
- Compact height: 32 px when needed in dense layouts.
- Touch-oriented height: preferably 44 px on narrow touch interfaces.
- Horizontal padding: 12–16 px.
- Provide disabled and loading states.
- Prevent repeated submissions while an action is processing.
- Use action labels that describe the result, such as **Save review** or **Retry processing**.

### 7.2 Status Labels

Status labels display concise, stable states.

Examples:

- Unreviewed.
- Under review.
- Uncertain.
- Confirmed by reviewer.
- False alert.
- Inconclusive.
- Processing.
- Failed.
- Unavailable.

Rules:

- Prefer a text label over an icon alone.
- Use semantic color only when it adds meaningful context.
- Keep label lengths short.
- Use the same label for the same state across all screens.
- Never collapse distinct states into a generic **Warning** label.

### 7.3 Incident Table

The incident table is a core reusable component.

Recommended columns:

- Event time.
- Source.
- Detection category.
- Reliability or uncertainty state.
- Review status.

Additional score information may be displayed where it adds value without overcrowding the row.

Behavior:

- Rows must be keyboard accessible.
- Clicking an incident opens its detail view.
- Row actions must not accidentally trigger row navigation.
- Column alignment should remain stable while sorting.
- Dates and numbers must align consistently.
- Long identifiers may be abbreviated in the list but must remain available in the detail screen.
- Filters must work on the underlying data, not merely change the displayed styling.
- Empty results must distinguish a genuinely empty dataset from a filter mismatch.

### 7.4 Metric Display

Use metric displays for a small number of meaningful summary values.

Each metric should include:

- Metric name.
- Value and unit, when available.
- Evaluation period.
- Data source or sample count where needed.
- A concise explanation or accessible reference to its definition.

Do not use a large value card for every available number.

For example, **False alerts per hour** is a useful metric only when the eligible monitored-video duration and counting rules are defined.

Avoid unqualified percentage changes or trend arrows without a meaningful comparison period.

### 7.5 Filter Controls

Filters should make the incident list easier to investigate.

Possible filters include:

- Time period.
- Source or camera.
- Detection category.
- Review status.

Requirements:

- Selected filters must be visibly identifiable.
- Users must be able to clear individual filters or reset the filter set.
- Filter labels must be understandable without technical knowledge.
- Applying filters must preserve the current screen context.
- Filtered results must be distinguished from the full dataset where ambiguity is possible.

### 7.6 Video Evidence Player

The evidence player is a primary incident-review component.

Requirements:

- Preserve the video's aspect ratio.
- Never stretch footage to fill a panel.
- Provide ordinary playback controls where the format supports them.
- Keep relevant timestamps visible.
- Indicate loading, unavailable, and failed media states.
- Use neutral surrounding surfaces to avoid competing with the video.
- Maintain a predictable player size within the incident-detail layout.
- Display still frames clearly when playable video is not available.
- Never imply that prerecorded footage is live.

If evidence playback fails, the rest of the incident detail screen should remain usable.

### 7.7 Evidence Metadata

Evidence metadata should be displayed as concise key-value pairs.

Examples include source identifier, event timestamp, clip interval, detector version, and assessment time.

- Align labels and values consistently.
- Use the same ordering across similar evidence records.
- Allow long values to wrap or expand without breaking the layout.
- Preserve the full value for identifiers and timestamps when it matters operationally.

### 7.8 Reliability Assessment Panel

This component summarizes the reliability layer's findings.

Possible sections:

- Video quality.
- Evidence sufficiency.
- Uncertainty reason.
- Available supporting observations.

Requirements:

- Use explicit labels rather than unexplained icons.
- Distinguish computed measurements from qualitative judgments.
- Do not invent a universal reliability percentage.
- Do not display a quality assessment if it has not been performed.
- Clearly communicate when an assessment failed to run.

### 7.9 Review Outcome Controls

The incident-detail screen should provide a clearly grouped review action.

Available outcomes:

- Confirmed by reviewer.
- False alert.
- Inconclusive or insufficient evidence.

Rules:

- Explain that this action records the operator's review.
- Do not automatically translate a review outcome into a crime classification or severity score.
- Make the selected outcome apparent before saving.
- Require explicit confirmation only when the operation is difficult to reverse or has consequential side effects.
- Show a saving state and a clear success or failure result.
- Preserve the original detector prediction.

### 7.10 Charts

Charts should answer an operational question, not serve as decoration.

Requirements:

- Use readable axes, units, legends, and date ranges.
- Include accessible labels or a text summary of important findings.
- Indicate missing or insufficient data.
- Keep the color mapping consistent for the same metric across screens.
- Do not use pie charts for metrics without a meaningful part-to-whole relationship.
- Do not imply a trend when there are too few data points.
- Prefer simple line charts for trends and bar charts for meaningful category comparisons.

Condition-specific comparisons must display sample counts and be appropriately qualified.

### 7.11 Alerts and Notifications

Use inline messages for persistent issues and toast notifications for short-lived operation results.

**Inline messages** are suitable for missing evidence, insufficient evaluation data, and source-processing failures.

**Toast messages** are suitable for outcomes such as a successfully saved review or a recoverable action failure.

Rules:

- Messages must be concise and specific.
- Failure messages should explain what happened and what the user can do next, when possible.
- Important issues must not disappear before the user can read them.
- Do not communicate important workflow state only through a temporary toast.

### 7.12 Dialogs

Use a dialog only when the user must make a focused decision or complete a short interaction without losing context.

- Keep the title explicit.
- Explain the consequence of the action.
- Use clear action labels.
- Close through an explicit action or an appropriately supported dismissal behavior.
- Trap keyboard focus while open and restore focus when closed.
- Avoid dialogs for lengthy forms or routine record inspection.

### 7.13 Tooltips

Use tooltips for brief clarifications of a metric, icon, or technical term.

Do not use tooltips to hide essential instructions, status explanations, or required information.

All tooltip information must remain available to keyboard users, and essential content must be accessible on touch devices.

---

## 8. Forms and Data Entry

### 8.1 General Form Rules

- Use visible labels above fields.
- Place short explanatory text near the field it describes.
- Mark required fields clearly.
- Show validation errors next to the relevant field.
- Preserve valid user-entered values after recoverable errors.
- Group related fields logically.
- Avoid asking for information that is unnecessary for the current task.
- Use appropriate input types for dates, numbers, identifiers, and text.

### 8.2 Review Forms

The review workflow should remain short.

Required input:

- Review outcome.

Optional input, if implemented:

- Review note.

Do not require long narrative descriptions to save a routine review.

### 8.3 Validation Behavior

- Validate when appropriate during entry and again on submission.
- Do not show errors before the user has had a reasonable opportunity to complete the field.
- Explain how to correct a validation error.
- Associate each error with its field.
- Keep the form and submitted values visible after an error.
- If submission fails because of a server problem, retain user input for retry.

### 8.4 Saving Behavior

When a form is submitted:

1. Disable repeated submission while processing.
2. Show a clear saving indicator.
3. Report success only after the application confirms the operation.
4. Preserve input and display a useful error if saving fails.

The interface must never display a success state merely because the user clicked the button.

---

## 9. Page-Level Layout Guidance

### 9.1 Login

**Purpose:** Provide controlled access to the application.

Layout:

- Compact authentication panel.
- Application name and short product descriptor.
- Clearly labeled authentication fields.
- One primary submit action.
- Inline validation and authentication errors.

Avoid marketing-style hero content, customer logos, feature grids, and decorative illustrations.

If the MVP uses predefined demonstration access, make the environment and access model explicit rather than presenting a nonfunctional sign-in form.

### 9.2 Operations Dashboard

**Purpose:** Give operators and supervisors an immediate overview of alert activity and system status.

Recommended structure:

1. Page heading and optional time-period context.
2. Small set of meaningful operational metrics.
3. Recent or unresolved incidents.
4. Source and processing status.
5. Reliability summary where sufficient data exists.

Layout rules:

- Prioritize actionable incidents over decorative charts.
- Keep summary metrics compact.
- Use one main incident table or list rather than repeating the same data in multiple widgets.
- Do not display empty KPI cards for metrics that cannot yet be calculated.
- Identify simulated and prerecorded data prominently when applicable.
- Use consistent widths and alignment for the table and surrounding sections.

### 9.3 Incident List

**Purpose:** Enable rapid scanning, filtering, and selection of candidate incidents.

Recommended structure:

1. Page title and total result count.
2. Filter row.
3. Incident table.
4. Pagination or another suitable result-navigation mechanism if needed.

Layout rules:

- The table should use most of the available content width.
- Keep filters compact and grouped.
- Avoid excessive row height.
- Highlight only the currently focused, hovered, or selected row.
- Show review status and reliability state independently.
- Preserve selected filters when returning from an incident detail view where practical.

### 9.4 Incident Detail and Evidence Review

**Purpose:** Provide enough evidence and context for a human to evaluate an alert.

On desktop, use a two-column layout.

**Primary column — Evidence**

- Video player or relevant still frames.
- Relevant event timestamps.
- Playback or frame-inspection controls where supported.
- Evidence availability and processing status.

**Secondary column — Incident information**

- Source and event metadata.
- Model-generated detection category and score.
- Video-quality assessment.
- Evidence-sufficiency and uncertainty information.
- Observation-based explanation, when available.
- Human review outcome controls.

Recommended proportions:

- Evidence column: approximately 60–65% of the content width.
- Incident-information column: approximately 35–40%.

These proportions may shift to preserve a usable video display.

Additional rules:

- Keep the incident identity and timestamp visible while reviewing evidence.
- Do not allow the sidebar of metadata to compress the video into an unusable size.
- Place review actions together near the end of the information workflow or in a stable action area.
- On narrower screens, stack evidence first, then metadata and review controls.
- Maintain the distinction between detector findings and the final review outcome.

### 9.5 Reliability Dashboard

**Purpose:** Explain how the system performs and where reliability gaps remain.

Recommended structure:

1. Page heading and evaluation context.
2. Dataset or metric-source identification.
3. Key metrics, including false alerts per hour, precision, and recall when available.
4. Detection delay and review time.
5. Condition-specific results when supported by sufficient data.

Layout rules:

- Prefer a small number of directly comparable charts.
- Place definitions and sample counts near the associated metrics.
- Display the evaluation timestamp and relevant detector version.
- Use identical definitions across comparisons.
- Distinguish benchmark results from operational metrics.
- Keep unavailable metrics visible as unavailable when their absence matters to interpretation.
- Do not present a polished chart when the dataset is too small to support a meaningful conclusion.

### 9.6 System Status and Sources

**Purpose:** Help technical administrators understand source and processing health.

Recommended structure:

1. Page heading.
2. Current input mode and processing status.
3. Configured source list.
4. Recent processing errors and diagnostic details.
5. Supported source-configuration controls.

Rules:

- Use concise status labels.
- Distinguish source unavailability from detector failure.
- Show the last successful processing time when known.
- Keep diagnostic details accessible without placing technical logs in the main operator workflow.
- When operating with prerecorded clips, describe the actual clip-processing state rather than implying live CCTV availability.

### 9.7 Evaluation Results

If evaluation results are implemented as a separate screen, use a simple structure:

1. Dataset and evaluation metadata.
2. Detector version and configuration.
3. Summary metrics.
4. Condition-specific breakdowns.
5. Processing failures, exclusions, and limitations.

The screen should support interpretation and comparison, not just display a collection of charts.

---

## 10. Loading, Empty, Error, and Uncertainty States

State design is part of the core product experience. Every primary page must define these states consistently.

### 10.1 Loading

Use lightweight indicators close to the content being loaded.

- Use a page-level loading state only when the page cannot function without its initial data.
- Use table-row placeholders for incident-list loading when practical.
- Load incident metadata independently from video evidence where possible.
- Keep already loaded information visible during secondary requests unless it becomes misleading.
- Avoid long decorative skeletons or simulated content that looks like real records.
- Where progress is unknown, use an indeterminate indicator rather than an invented percentage.

### 10.2 Empty States

Empty states must explain the actual reason for the absence of content.

Examples:

**No incidents**

"No incidents are available for this period."

**No filtered results**

"No incidents match these filters. Clear one or more filters to see more results."

**No evaluation data**

"Reliability metrics are unavailable because no completed evaluation data is available."

**No sources configured**

"No video sources are configured for this environment."

Empty states should include a relevant next action only when one exists and is supported by the implementation.

Do not use decorative illustrations or large blank-state graphics. A simple icon, short explanation, and relevant action are sufficient.

### 10.3 Error States

Errors must be specific enough to help users recover without exposing secrets or internal implementation details.

Examples:

**Dashboard data unavailable**

"Dashboard data could not be loaded. Try again."

**Evidence unavailable**

"This evidence cannot currently be accessed. The rest of the incident details remain available."

**Processing failure**

"This video could not be processed. Check the source and processing status."

**Review submission failure**

"Your review could not be saved. Your selection has been retained; try again."

Requirements:

- Explain what failed.
- State the impact on the current task.
- Provide retry or recovery when appropriate.
- Preserve user input after recoverable failures.
- Distinguish a technical failure from a negative incident classification.
- Avoid showing raw stack traces to ordinary users.

### 10.4 Uncertainty States

Uncertainty is a first-class product state and requires more than a generic warning icon.

The interface should show:

- The uncertainty label.
- The reason, where known.
- The evidence available for review.
- Any missing or failed assessment.
- A clear distinction between the system's uncertainty and the human review outcome.

Example:

**Insufficient visual evidence**

"The available footage does not support a reliable interpretation of this event."

Do not label the event a false alert solely because the evidence is insufficient.

### 10.5 Unavailable vs. Failed

These states must remain distinct.

- **Unavailable:** Data does not exist, is not accessible, or cannot currently be provided.
- **Failed:** An operation was attempted but did not complete successfully.
- **Uncertain:** The available evidence does not support a sufficiently reliable conclusion.
- **False alert:** An authorized reviewer or validated evaluation process has classified the detection as a false positive.
- **Not evaluated:** A reliability or benchmark assessment has not been performed.

Use these distinctions consistently in labels, metrics, tables, and incident details.

---

## 11. Interaction and Animation

### 11.1 Interaction Principles

Interactions should provide feedback without distracting the operator.

- Buttons must respond immediately with a visible interaction state.
- Selected navigation must remain visually distinct from hover.
- Tables must provide predictable row selection and focus behavior.
- Forms must communicate saving and completion clearly.
- Media controls must behave like standard video controls.
- Failed operations must allow recovery where possible.
- An action must not silently discard a user's review or filter context.

### 11.2 Motion

Use subtle transitions only where they help explain a state change.

Recommended behavior:

- Hover and focus transitions: approximately 100–150 ms.
- Small menu or popover transitions: approximately 120–180 ms.
- Dialog transitions: approximately 150–200 ms.
- Avoid elaborate page transitions or animated backgrounds.

Do not animate every card, number, chart, or table row.

### 11.3 Operational Updates

If real-time event updates are implemented:

- New incidents must enter the list without making the entire page jump unexpectedly.
- Preserve the user's current scroll and selection where practical.
- Indicate when fresh items are available rather than forcing the user away from the incident being reviewed.
- Do not represent simulated data changes as live detections.

### 11.4 Review Submission

When saving a review:

1. Show the chosen outcome.
2. Prevent duplicate submissions while the request is in progress.
3. Show a success confirmation after persistence succeeds.
4. Preserve the original prediction.
5. Keep the record and its new review status synchronized.
6. If saving fails, preserve the selection and explain how to retry.

### 11.5 Destructive and Irreversible Actions

Destructive actions are not part of the required core review workflow.

If a later approved feature introduces a genuinely destructive action, require appropriate confirmation, explain the consequence, and provide a recovery strategy where feasible.

### 11.6 Reduced Motion

Respect the operating system's reduced-motion preference. The application must remain fully usable when animations are reduced or disabled.

---

## 12. Responsive Behavior

The initial product is desktop-first because operators need to inspect video evidence alongside detailed incident metadata.

However, core functionality should remain usable on smaller screens.

### 12.1 Desktop — 1200 px and Above

- Full sidebar.
- Multi-column incident-detail layout.
- Wide incident table.
- Reliability charts arranged for comparison.
- Full operational dashboard layout.

### 12.2 Small Desktop and Tablet — 768 to 1199 px

- Sidebar may collapse or become narrower.
- Incident tables may hide lower-priority columns, provided those details remain available in incident views.
- Incident-detail columns may use a narrower proportional layout or stack vertically.
- Filter groups may wrap onto additional lines.
- Metric sections may reduce their column count.
- Main content must remain readable without horizontal page scrolling.

### 12.3 Mobile — Below 768 px

Mobile support is for access and limited review, not for matching desktop analytical density.

- Use a compact navigation drawer or equivalent responsive navigation.
- Stack incident evidence, metadata, and review controls vertically.
- Keep primary review actions accessible.
- Convert dense tables to stacked records or a simplified layout.
- Preserve timestamps, source identifiers, detection state, and human review status.
- Make controls comfortable for touch interaction.
- Avoid layouts that require horizontal scrolling for ordinary incident-review actions.

### 12.4 Responsive Rules

- Use fluid content widths and sensible minimums.
- Avoid hard-coded page widths.
- Preserve media aspect ratios.
- Allow metadata to wrap without clipping.
- Prevent action buttons from overlapping status information.
- Do not hide uncertainty warnings simply to save space.
- Test long incident IDs, long source names, and narrow viewports.

---

## 13. Accessibility Requirements

The product must support keyboard operation, readable contrast, and clear communication for users with varied accessibility needs.

### 13.1 Standards

Target **WCAG 2.2 Level AA** for the application interface.

### 13.2 Keyboard Navigation

- Every interactive element must be reachable through the keyboard.
- Focus order must match the visual and task hierarchy.
- Visible focus indicators must be present.
- There must be no keyboard traps outside correctly managed dialogs and drawers.
- Table interactions must not depend exclusively on a mouse.
- Hover-only information must have a keyboard-accessible equivalent.

### 13.3 Contrast

- Normal text should meet a minimum contrast ratio of 4.5:1.
- Large text should meet a minimum contrast ratio of 3:1.
- Meaningful graphical components and control boundaries should meet applicable non-text contrast requirements.
- Disabled-state styling must remain distinguishable without becoming unreadable.

### 13.4 Screen Readers

- Interactive controls must have clear accessible names.
- Form fields must have programmatically associated labels.
- Errors must be associated with the relevant controls.
- Tables must use appropriate header semantics.
- Status changes and important operation results must be communicated accessibly.
- Icon-only buttons must provide accessible labels.
- Meaningful chart findings must be available as text.

### 13.5 Color Independence

Do not rely on red, amber, green, or blue alone to communicate status.

Always pair meaningful color with labels, icons, or other visible context.

### 13.6 Video Accessibility

Where supported by the content and media format:

- Provide standard keyboard-operable playback controls.
- Make timestamps and evidence metadata accessible.
- Do not rely exclusively on visual markings to communicate important evidence.
- Preserve access to the incident record when the video cannot be played.

### 13.7 Cognitive Accessibility

- Use consistent terminology.
- Keep alert and review labels predictable.
- Prefer concise sentences.
- Avoid ambiguous symbols and unexplained abbreviations.
- Clearly distinguish user actions, model findings, and system status.
- Avoid motion or flashing that could distract from evidence review.

---

## 14. Content and Writing Guidelines

### 14.1 Tone

Use a professional, neutral, evidence-based tone.

The product should sound like an operational system, not a marketing page or conversational AI assistant.

### 14.2 Labels

Prefer precise labels:

- "Model detection" rather than "AI verdict".
- "Uncertain" rather than "Danger detected".
- "Evidence unavailable" rather than "Something went wrong" when the evidence is specifically unavailable.
- "Confirmed by reviewer" rather than "Verified crime".
- "False alert" only when the detection has been classified as a false positive.
- "Video quality assessment" rather than "AI confidence".
- "Evaluation sample count" rather than an unexplained number beneath a chart.

### 14.3 Metric Language

Every quantitative value must describe what it measures.

Examples:

- False alerts per hour.
- Precision.
- Recall.
- Median detection delay.
- Median review time.
- Number of evaluated events.
- Eligible monitored-video duration.

Avoid vague labels such as **Accuracy score**, **Safety score**, or **AI reliability** unless the calculation and meaning are explicitly defined.

### 14.4 Error Language

Error messages must be direct and actionable.

Do not blame the user or use alarmist language.

Do not tell the operator that a serious incident occurred when the system only produced a candidate detection.

### 14.5 Dates and Time

- Use one consistent date and time format throughout the application.
- Display timestamps in the configured deployment's local timezone.
- Preserve timezone information in underlying data.
- If a timestamp's timezone is unknown, do not silently imply certainty.
- Use a consistent representation for event times, ingestion times, review times, and evaluation timestamps.
- When seconds materially affect incident interpretation, display them.

---

## 15. Data Visualization Guidelines

### 15.1 Purpose

Charts must help supervisors understand operational performance, compare conditions, or identify measurable trends.

A chart must not be added only to make the dashboard look more sophisticated.

### 15.2 Chart Selection

| Question | Preferred visualization |
|---|---|
| How did false alerts change over time? | Line chart |
| How does performance differ across conditions? | Bar chart |
| How many incidents fall into each review status? | Compact bar chart or direct count summary |
| How do precision and recall vary across evaluation runs? | Line chart or grouped comparison |
| What percentage of a total belongs to a category? | Part-to-whole chart only when the denominator is meaningful |

### 15.3 Chart Rules

- Label both axes when the units are not self-evident.
- Include the time period.
- Use consistent metric colors across screens.
- Avoid unnecessary gradients and 3D effects.
- Show sample counts when they affect interpretation.
- Indicate missing values and excluded samples.
- Avoid smoothing that conceals important variations.
- Provide a concise textual interpretation where it improves usability.

### 15.4 Data Integrity

The interface must not:

- Display fabricated data as measured output.
- Imply that a metric is live when it comes from a completed evaluation.
- Hide failed samples that materially affect interpretation.
- Compare runs with incompatible metric definitions without a clear warning.
- Show percentage improvements without a defined baseline.

---

## 16. Design Tokens and Consistency Rules

The implementation must define reusable tokens for:

- Backgrounds and surfaces.
- Text and border colors.
- Primary and semantic colors.
- Typography sizes and weights.
- Spacing.
- Border radii.
- Control heights.
- Focus indicators.
- Layering for navigation menus, dialogs, and overlays.
- Animation duration and motion preferences.

Components should consume these shared tokens rather than defining their own unrelated visual values.

### 16.1 Consistency Requirements

- One semantic status must use the same label and meaning across the application.
- The same type of primary action must look and behave consistently.
- Identical interaction patterns must use identical focus and disabled states.
- Tables must share typography, spacing, and selection behavior.
- Metric cards must share a consistent hierarchy.
- Forms must share label, validation, and submission patterns.
- Dialogs, inline messages, and toasts must have distinct and consistent purposes.

Do not create multiple near-identical components merely because they appear on different pages.

---

## 17. Implementation Guidance for the Design System

1. Treat `PRD.md` as the source of truth for product functionality and `DESIGN.md` as the source of truth for visual design and UX behavior.
2. Inspect the existing repository before creating or modifying the interface.
3. Reuse existing components and libraries when they satisfy these guidelines.
4. Establish shared design tokens before applying page-specific styling.
5. Build the application shell and core reusable components before polishing individual screens.
6. Prioritize the incident list, incident detail, evidence viewer, and review workflow because they represent the core product experience.
7. Implement explicit states for loading, empty results, failures, and uncertainty.
8. Ensure the visual hierarchy distinguishes detector results, reliability assessments, and human decisions.
9. Do not add new product features merely to fill space or make the interface look complete.
10. Do not use placeholder metrics or simulated live activity without clearly identifying their source.
11. Test responsive layouts and keyboard interactions before considering the UI complete.
12. Verify contrast and accessibility of status indicators, forms, charts, dialogs, and navigation.
13. Document any necessary departure from this design system instead of introducing undocumented inconsistencies.

---

## 18. Design Acceptance Criteria

The implementation satisfies this specification when:

- [ ] All core pages share the same application shell, typography, spacing, and color tokens.
- [ ] The interface follows the evidence-first visual direction.
- [ ] Incident tables are scannable and support the specified filters.
- [ ] Incident detail provides a usable evidence area and a clear distinction between model findings and human review.
- [ ] Uncertainty and missing evidence are explicit and cannot be mistaken for a confirmed event.
- [ ] Reliability metrics display their context and do not imply unsupported certainty.
- [ ] Loading, empty, error, failed, and unavailable states are implemented consistently.
- [ ] Buttons, form fields, status labels, tables, and dialogs use reusable component patterns.
- [ ] The interface is usable on desktop, tablet, and mobile-sized viewports.
- [ ] Keyboard focus is visible and all essential actions can be completed without a mouse.
- [ ] Color is not the sole means of communicating status.
- [ ] Motion is restrained and respects reduced-motion preferences.
- [ ] No decorative elements obscure evidence or reduce operational clarity.
- [ ] Simulated and prerecorded content is clearly identified.
- [ ] No fabricated metric, unsupported performance claim, or unimplemented feature is presented as real.
- [ ] The resulting interface feels like a focused public-space incident review tool rather than a generic SaaS template.

---

## 19. Final Design Definition

SafeCity AI should look and behave like a dependable operational workspace: quiet, precise, evidence-centered, and transparent about its limitations.

Its visual hierarchy must consistently prioritize:

1. The incident and its supporting evidence.
2. The reliability and uncertainty of the detection.
3. The human review decision.
4. The measurable performance of the system.

The interface must communicate uncertainty without creating unnecessary alarm, present quantitative results without overstating their meaning, and help operators make informed decisions without pretending that automated detections are ground truth.

**The defining design principle is simple: make evidence easy to inspect, uncertainty impossible to miss, and every operational decision clear.**
