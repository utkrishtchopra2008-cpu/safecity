import { useQuery } from '@tanstack/react-query';
import { Navigate } from 'react-router-dom';

import { ApiError, requestJson, type CurrentUser } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { Surface } from '../components/Surface';

type Metric = {
  metric_key: string;
  value: number | null;
  unit: string | null;
  availability_status: 'available' | 'unavailable' | 'insufficient_data';
  sample_count: number | null;
  numerator: number | null;
  denominator: number | null;
  scope_key: string;
  unavailable_reason: string | null;
  evaluation_id: string | null;
  dataset_name: string | null;
  dataset_version: string | null;
  data_source: 'labeled_evaluation';
};

type ReliabilityResponse = { metrics: Metric[]; provenance: string };

export function ReliabilityPage() {
  const user = useQuery({
    queryKey: ['current-user'],
    queryFn: () => requestJson<CurrentUser>('/auth/me'),
    retry: false,
  });
  const summary = useQuery({
    queryKey: ['reliability-summary'],
    queryFn: () => requestJson<ReliabilityResponse>('/reliability/summary'),
    enabled: user.isSuccess,
  });
  if (user.isLoading) return <p role="status">Checking your session…</p>;
  if (user.error instanceof ApiError && user.error.status === 401)
    return <Navigate to="/login" replace />;
  if (user.isError) return <p role="alert">Your session could not be checked. Sign in again.</p>;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Measured performance"
        title="Reliability"
        description="Metrics are shown only when a labeled evaluation supports them. Operational reviews and public context are not treated as benchmark labels."
      />
      {summary.isLoading ? <p role="status">Loading evaluation metrics…</p> : null}
      {summary.isError ? (
        <Surface>
          <h2>Metrics could not be loaded</h2>
          <p>{summary.error.message}</p>
          <button className="button button--primary" onClick={() => void summary.refetch()}>
            Retry
          </button>
        </Surface>
      ) : null}
      {summary.isSuccess ? (
        <>
          <div className="metric-grid">
            {summary.data.metrics.map((metric, index) => (
              <Surface
                key={`${metric.metric_key}-${metric.evaluation_id ?? 'none'}-${metric.scope_key}-${index}`}
              >
                <div className="section-heading">
                  <h2>{metric.metric_key.replaceAll('_', ' ')}</h2>
                  <StatusBadge
                    tone={metric.availability_status === 'available' ? 'success' : 'neutral'}
                  >
                    {metric.availability_status.replaceAll('_', ' ')}
                  </StatusBadge>
                </div>
                <p className="metric-value">
                  {metric.value === null
                    ? 'Unavailable'
                    : `${metric.value}${metric.unit ? ` ${metric.unit}` : ''}`}
                </p>
                {metric.sample_count !== null ? <p>Sample count: {metric.sample_count}</p> : null}
                {metric.dataset_name ? (
                  <p>
                    Dataset: {metric.dataset_name} · {metric.dataset_version}
                  </p>
                ) : null}
                <p>{metric.unavailable_reason ?? `Scope: ${metric.scope_key}`}</p>
              </Surface>
            ))}
          </div>
          <Surface>
            <h2>Provenance</h2>
            <p>{summary.data.provenance}</p>
          </Surface>
        </>
      ) : null}
    </div>
  );
}
