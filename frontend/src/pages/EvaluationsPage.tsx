import { useQuery } from '@tanstack/react-query';
import { Navigate } from 'react-router-dom';

import { ApiError, requestJson, type CurrentUser } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { Surface } from '../components/Surface';

type Metric = {
  metric_key: string;
  scope_key: string;
  availability_status: 'available' | 'unavailable' | 'insufficient_data';
  value: number | null;
  unit: string | null;
  sample_count: number | null;
  unavailable_reason: string | null;
};

type Evaluation = {
  id: string;
  dataset_name: string;
  dataset_version: string;
  detector_name: string;
  detector_version: string | null;
  status: 'pending' | 'running' | 'completed' | 'failed';
  eligible_asset_count: number;
  excluded_asset_count: number;
  failed_asset_count: number;
  created_at: string;
  metrics: Metric[];
};

type EvaluationPageResponse = {
  items: Evaluation[];
  page: number;
  page_size: number;
  has_more: boolean;
  total_count: number;
};

export function EvaluationsPage() {
  const user = useQuery({
    queryKey: ['current-user'],
    queryFn: () => requestJson<CurrentUser>('/auth/me'),
    retry: false,
  });
  const evaluations = useQuery({
    queryKey: ['evaluations'],
    queryFn: () => requestJson<EvaluationPageResponse>('/evaluations?page=1&page_size=50'),
    enabled: user.isSuccess,
  });
  if (user.isLoading) return <p role="status">Checking your session…</p>;
  if (user.error instanceof ApiError && user.error.status === 401)
    return <Navigate to="/login" replace />;
  if (user.isError) return <p role="alert">Your session could not be checked. Sign in again.</p>;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Benchmark results"
        title="Evaluations"
        description="Evaluation results are tied to labeled dataset versions and detector versions. Unavailable values are never represented as zero."
      />
      {evaluations.isLoading ? <p role="status">Loading evaluation runs…</p> : null}
      {evaluations.isError ? (
        <Surface>
          <h2>Evaluation runs could not be loaded</h2>
          <p>{evaluations.error.message}</p>
          <button className="button button--primary" onClick={() => void evaluations.refetch()}>
            Retry
          </button>
        </Surface>
      ) : null}
      {evaluations.isSuccess && evaluations.data.items.length === 0 ? (
        <Surface>
          <h2>No evaluation runs</h2>
          <p>
            No labeled evaluation results are recorded. A verified detector is not currently
            configured, so new runs cannot be started.
          </p>
        </Surface>
      ) : null}
      {evaluations.isSuccess && evaluations.data.items.length > 0 ? (
        <div className="evaluation-list">
          {evaluations.data.items.map((run) => (
            <Surface key={run.id}>
              <div className="section-heading">
                <h2>
                  {run.dataset_name} · {run.dataset_version}
                </h2>
                <StatusBadge tone={run.status === 'completed' ? 'success' : 'neutral'}>
                  {run.status}
                </StatusBadge>
              </div>
              <p>
                Detector: {run.detector_name} {run.detector_version ?? 'version not reported'}
              </p>
              <p>
                Assets: {run.eligible_asset_count} eligible · {run.excluded_asset_count} excluded ·{' '}
                {run.failed_asset_count} failed
              </p>
              {run.metrics.length === 0 ? <p>No calculated metrics are available.</p> : null}
              <ul className="evaluation-metrics">
                {run.metrics.map((metric) => (
                  <li key={`${metric.metric_key}-${metric.scope_key}`}>
                    <strong>{metric.metric_key.replaceAll('_', ' ')}</strong>:{' '}
                    {metric.value === null
                      ? (metric.unavailable_reason ?? metric.availability_status)
                      : `${metric.value}${metric.unit ? ` ${metric.unit}` : ''}`}
                    {metric.sample_count !== null ? ` · n=${metric.sample_count}` : ''}
                  </li>
                ))}
              </ul>
            </Surface>
          ))}
        </div>
      ) : null}
    </div>
  );
}
