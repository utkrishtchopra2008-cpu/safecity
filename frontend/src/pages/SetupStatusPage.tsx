import { ArrowUpRight, CheckCircle2, CircleDashed, ShieldCheck } from 'lucide-react';

import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { Surface } from '../components/Surface';
import { API_BASE_URL } from '../api/client';

const foundationItems = [
  {
    title: 'Frontend shell and routes',
    detail: 'React, TypeScript, Vite, and shared design tokens are configured.',
    status: 'Ready',
    ready: true,
  },
  {
    title: 'Backend liveness',
    detail: 'The FastAPI service exposes /health/live and /health/ready.',
    status: 'Scaffolded',
    ready: true,
  },
  {
    title: 'Database and application workflows',
    detail: 'Persistence, authentication, incidents, and video processing are planned next.',
    status: 'Not implemented',
    ready: false,
  },
  {
    title: 'TinyFish public context',
    detail: 'Configuration is present but disabled. No provider request is made by this scaffold.',
    status: 'Disabled by default',
    ready: false,
  },
] as const;

export function SetupStatusPage() {
  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Workspace setup"
        title="Foundation is in place"
        description="The application shell is ready for the next implementation phase. Operational workflows are not enabled in this setup build."
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
        <StatusBadge tone="info">Foundation only</StatusBadge>
      </Surface>

      <section aria-labelledby="setup-checklist-heading" className="section-stack">
        <div className="section-heading">
          <div>
            <h2 id="setup-checklist-heading">Setup checklist</h2>
            <p>These states describe the scaffold, not live surveillance or processing status.</p>
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
            <dd>TinyFish — disabled</dd>
          </div>
          <div>
            <dt>Data mode</dt>
            <dd>No video source connected</dd>
          </div>
        </dl>
        <p className="surface-footnote">
          Next step: connect the database and validate the backend development loop before adding
          feature endpoints.
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
