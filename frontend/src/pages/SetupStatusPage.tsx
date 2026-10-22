import { ArrowUpRight, CheckCircle2, CircleDashed, ShieldCheck } from 'lucide-react';

import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { Surface } from '../components/Surface';
import { API_BASE_URL } from '../api/client';

const foundationItems = [
  {
    title: 'Session sign-in and CSRF protection',
    detail:
      'The API uses server-managed sessions; browser state does not store credentials or session tokens.',
    status: 'Implemented',
    ready: true,
  },
  {
    title: 'Candidate-event review',
    detail: 'Incident list, detail, and human review use typed API routes.',
    status: 'Partial',
    ready: true,
  },
  {
    title: 'Private upload and processing',
    detail:
      'Uploads are validated and queued. Processing requires private Supabase Storage; detector models are an explicit local configuration.',
    status: 'Configuration required',
    ready: false,
  },
  {
    title: 'Detector, evaluation, and public context',
    detail:
      'Pinned object and face-region models can report bounded observations; incident classification and labeled evaluation require an approved event model and dataset. Public context is optional.',
    status: 'Partial',
    ready: false,
  },
] as const;

export function SetupStatusPage() {
  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Workspace setup"
        title="Implementation status"
        description="SafeCity AI provides authenticated review and source workflows. Video object observations, private storage, evaluation data, and external context depend on explicit configuration."
      />

      <Surface className="intro-surface">
        <div className="intro-icon" aria-hidden="true">
          <ShieldCheck size={25} />
        </div>
        <div className="intro-copy">
          <h2>Evidence-first by design</h2>
          <p>
            SafeCity AI is being built to help authorized operators review candidate events with
            evidence, uncertainty, and clear provenance. A model output is not a human conclusion.
          </p>
        </div>
        <StatusBadge tone="info">Partial implementation</StatusBadge>
      </Surface>

      <section aria-labelledby="setup-checklist-heading" className="section-stack">
        <div className="section-heading">
          <div>
            <h2 id="setup-checklist-heading">Setup checklist</h2>
            <p>
              These states describe implemented capability, not live surveillance or detector
              performance.
            </p>
          </div>
        </div>
        <div className="checklist">
          {foundationItems.map((item) => (
            <article className="checklist-item" key={item.title}>
              <span
                className={`checklist-icon ${item.ready ? 'is-ready' : 'is-pending'}`}
                aria-hidden="true"
              >
                {item.ready ? <CheckCircle2 size={19} /> : <CircleDashed size={19} />}
              </span>
              <div className="checklist-copy">
                <h3>{item.title}</h3>
                <p>{item.detail}</p>
              </div>
              <StatusBadge tone={item.ready ? 'success' : 'neutral'}>{item.status}</StatusBadge>
            </article>
          ))}
        </div>
      </section>

      <Surface className="configuration-surface">
        <div className="section-heading">
          <div>
            <h2>Client configuration</h2>
            <p>The API base path is public configuration; it contains no credentials.</p>
          </div>
          <StatusBadge tone="neutral">Configured</StatusBadge>
        </div>
        <dl className="config-grid">
          <div>
            <dt>API base path</dt>
            <dd>
              <code>{API_BASE_URL}</code>
            </dd>
          </div>
          <div>
            <dt>Context provider</dt>
            <dd>TinyFish — optional backend configuration</dd>
          </div>
          <div>
            <dt>Data mode</dt>
            <dd>No video source connected</dd>
          </div>
        </dl>
        <p className="surface-footnote">
          Object observations are not event classifications, and the absence of a model observation
          does not establish that an incident did not occur. No benchmark metric is available until
          a permitted labeled dataset is configured.
        </p>
        <a
          className="text-link"
          href="https://github.com/utkrishtchopra2008-cpu/safecity/blob/main/IMPLEMENTATION_PLAN.md"
          target="_blank"
          rel="noreferrer"
        >
          View implementation plan <ArrowUpRight size={15} aria-hidden="true" />
        </a>
      </Surface>
    </div>
  );
}
