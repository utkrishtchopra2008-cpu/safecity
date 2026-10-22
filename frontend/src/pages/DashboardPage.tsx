import { useQuery } from '@tanstack/react-query';
import { Link, Navigate } from 'react-router-dom';

import { ApiError, requestJson, type CurrentUser } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { Surface } from '../components/Surface';

type Summary = {
  period_label: string;
  period_start: string | null;
  period_end: string | null;
  incident_counts: Record<string, number>;
  recent_incidents: {
    id: string;
    source_id: string;
    received_at: string;
    detection_category: string;
    review_status: string;
  }[];
  source_counts: Record<string, number>;
  job_counts: Record<string, number>;
  reliability_metrics_available: boolean;
};

export function DashboardPage() {
  const user = useQuery({
    queryKey: ['current-user'],
    queryFn: () => requestJson<CurrentUser>('/auth/me'),
    retry: false,
  });
  const summary = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: () => requestJson<Summary>('/dashboard/summary'),
    enabled: user.isSuccess,
  });
  if (user.isLoading) return <p role="status">Checking your session…</p>;
  if (user.error instanceof ApiError && user.error.status === 401)
    return <Navigate to="/login" replace />;
  if (user.isError) return <p role="alert">Your session could not be checked. Sign in again.</p>;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Operations"
        title="Dashboard"
        description="A summary of persisted candidate events and processing status. Candidate events are not confirmed incidents."
      />
      {summary.isLoading ? <p role="status">Loading operational summary…</p> : null}
      {summary.isError ? (
        <Surface>
          <h2>Dashboard could not be loaded</h2>
          <p>{summary.error.message}</p>
          <button className="button button--primary" onClick={() => void summary.refetch()}>
            Retry
          </button>
        </Surface>
      ) : null}
      {summary.isSuccess ? (
        <>
          <p>
            Period: {summary.data.period_label}
            {summary.data.period_start
              ? ` · from ${new Date(summary.data.period_start).toLocaleString()}`
              : ''}
            {summary.data.period_end
              ? ` · through ${new Date(summary.data.period_end).toLocaleString()}`
              : ''}
          </p>
          <div className="metric-grid">
            <Surface>
              <h2>Awaiting human review</h2>
              <p className="metric-value">{summary.data.incident_counts.unreviewed ?? 0}</p>
            </Surface>
            <Surface>
              <h2>Reviewed</h2>
              <p className="metric-value">{summary.data.incident_counts.reviewed ?? 0}</p>
            </Surface>
            <Surface>
              <h2>Reliability metrics</h2>
              <p>
                <StatusBadge
                  tone={summary.data.reliability_metrics_available ? 'success' : 'neutral'}
                >
                  {summary.data.reliability_metrics_available ? 'Available' : 'Unavailable'}
                </StatusBadge>
              </p>
            </Surface>
          </div>
          <Surface>
            <div className="section-heading">
              <div>
                <h2>Recent candidate events</h2>
                <p>Detector observations require human interpretation.</p>
              </div>
              <Link to="/incidents">View all</Link>
            </div>
            {summary.data.recent_incidents.length ? (
              <ul>
                {summary.data.recent_incidents.map((incident) => (
                  <li key={incident.id}>
                    <Link to={`/incidents/${incident.id}`}>{incident.detection_category}</Link> ·{' '}
                    {new Date(incident.received_at).toLocaleString()} · {incident.review_status}
                  </li>
                ))}
              </ul>
            ) : (
              <p>No candidate events are recorded for this period.</p>
            )}
          </Surface>
          <Surface>
            <h2>Processing state</h2>
            <p>
              Sources:{' '}
              {Object.entries(summary.data.source_counts)
                .map(([state, count]) => `${state} ${count}`)
                .join(' · ') || 'No sources recorded'}
            </p>
            <p>
              Jobs:{' '}
              {Object.entries(summary.data.job_counts)
                .map(([state, count]) => `${state} ${count}`)
                .join(' · ') || 'No jobs recorded'}
            </p>
            <p>
              Quality sampling does not generate event detections. Worker liveness is not reported
              by this API.
            </p>
          </Surface>
        </>
      ) : null}
    </div>
  );
}
