import { useQuery } from '@tanstack/react-query';
import { Link, Navigate } from 'react-router-dom';

import { ApiError, requestJson, type CurrentUser } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { Surface } from '../components/Surface';

type Source = {
  id: string;
  name: string;
  source_type: string;
  status: string;
  created_at: string;
  last_processed_at: string | null;
  context_area_label: string | null;
  context_retrieval_enabled: boolean;
};

type SystemStatus = {
  status: 'available' | 'degraded';
  sources: Record<string, number>;
  jobs: Record<string, number>;
};

export function SystemStatusPage() {
  const user = useQuery({
    queryKey: ['current-user'],
    queryFn: () => requestJson<CurrentUser>('/auth/me'),
    retry: false,
  });
  const sources = useQuery({
    queryKey: ['sources'],
    queryFn: () => requestJson<Source[]>('/sources'),
    enabled: user.isSuccess,
  });
  const status = useQuery({
    queryKey: ['system-status'],
    queryFn: () => requestJson<SystemStatus>('/system/status'),
    enabled: user.isSuccess,
  });

  if (user.isLoading) return <p role="status">Checking your session…</p>;
  if (user.error instanceof ApiError && user.error.status === 401)
    return <Navigate to="/login" replace />;
  if (user.isError) return <p role="alert">Your session could not be checked. Sign in again.</p>;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Sources and processing"
        title="System status"
        description="Source state and queued processing status. A queued upload does not mean video analysis has completed."
        actions={
          status.data ? (
            <StatusBadge tone={status.data.status === 'available' ? 'success' : 'warning'}>
              {status.data.status}
            </StatusBadge>
          ) : null
        }
      />
      {sources.isLoading || status.isLoading ? (
        <p role="status">Loading source and job status…</p>
      ) : null}
      {sources.isError || status.isError ? (
        <Surface>
          <h2>Status could not be loaded</h2>
          <p>{sources.error?.message ?? status.error?.message}</p>
          <button
            className="button button--primary"
            onClick={() => {
              void sources.refetch();
              void status.refetch();
            }}
          >
            Retry
          </button>
        </Surface>
      ) : null}
      {status.isSuccess ? (
        <Surface>
          <h2>Processing jobs</h2>
          {Object.keys(status.data.jobs).length ? (
            <ul>
              {Object.entries(status.data.jobs).map(([state, count]) => (
                <li key={state}>
                  {state}: {count}
                </li>
              ))}
            </ul>
          ) : (
            <p>No job totals are available to this role.</p>
          )}
          <p>
            The API does not report worker liveness. The configured worker records bounded video
            quality observations only; it does not generate event detections.
          </p>
        </Surface>
      ) : null}
      {sources.isSuccess ? (
        <Surface>
          <h2>Configured sources</h2>
          {sources.data.length ? (
            <ul className="source-list">
              {sources.data.map((source) => (
                <li key={source.id}>
                  <div>
                    <strong>{source.name}</strong>
                    <span>
                      {source.source_type} · created {new Date(source.created_at).toLocaleString()}
                    </span>
                  </div>
                  <StatusBadge
                    tone={
                      source.status === 'ready'
                        ? 'success'
                        : source.status === 'failed'
                          ? 'critical'
                          : 'warning'
                    }
                  >
                    {source.status}
                  </StatusBadge>
                  {source.context_retrieval_enabled ? (
                    <Link to={`/sources/${source.id}/context`}>Public context</Link>
                  ) : (
                    <span>Public context disabled</span>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p>No sources are configured.</p>
          )}
        </Surface>
      ) : null}
    </div>
  );
}
