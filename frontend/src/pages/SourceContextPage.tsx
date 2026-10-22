import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Link, Navigate, useParams } from 'react-router-dom';

import { ApiError, requestJson, type CurrentUser } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { Surface } from '../components/Surface';

type ContextItem = {
  id: string;
  topic: string;
  title: string;
  publisher: string | null;
  source_domain: string;
  source_url: string;
  summary: string;
  published_at: string | null;
  retrieved_at: string;
  freshness_status: 'current' | 'stale' | 'unknown';
  processing_job_id: string;
};

type ContextPage = {
  items: ContextItem[];
  page: number;
  page_size: number;
  has_more: boolean;
};

type SourceSummary = {
  id: string;
  name: string;
  context_area_label: string | null;
  context_retrieval_enabled: boolean;
};

type Accepted = { source_id: string; job_id: string; status: 'pending' };

export function SourceContextPage() {
  const { sourceId = '' } = useParams();
  const queryClient = useQueryClient();
  const [jobId, setJobId] = useState<string>();
  const user = useQuery({
    queryKey: ['current-user'],
    queryFn: () => requestJson<CurrentUser>('/auth/me'),
    retry: false,
  });
  const contextItems = useQuery({
    queryKey: ['source-context', sourceId],
    queryFn: () => requestJson<ContextPage>(`/sources/${sourceId}/context?page=1&page_size=50`),
    enabled: user.isSuccess && Boolean(sourceId),
  });
  const source = useQuery({
    queryKey: ['source', sourceId],
    queryFn: () => requestJson<SourceSummary>(`/sources/${sourceId}`),
    enabled: user.isSuccess && Boolean(sourceId),
  });
  const job = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => requestJson<{ status: string }>(`/jobs/${jobId}`),
    enabled: Boolean(jobId) && user.isSuccess,
    refetchInterval: (query) =>
      query.state.data?.status === 'pending' || query.state.data?.status === 'running'
        ? 2_000
        : false,
  });
  const refresh = useMutation({
    mutationFn: () =>
      requestJson<Accepted>(`/sources/${sourceId}/context-refresh`, {
        method: 'POST',
        body: JSON.stringify({ topics: [], time_window_hours: 24 }),
      }),
    onSuccess: async (accepted) => {
      setJobId(accepted.job_id);
      await queryClient.invalidateQueries({ queryKey: ['source-context', sourceId] });
    },
  });

  if (user.isLoading) return <p role="status">Checking your session…</p>;
  if (user.error instanceof ApiError && user.error.status === 401)
    return <Navigate to="/login" replace />;
  if (user.isError) return <p role="alert">Your session could not be checked. Sign in again.</p>;

  const canRefresh = user.data?.role === 'supervisor' || user.data?.role === 'technical_admin';
  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="External public information"
        title="Source context"
        description="Public context is attributed external information. It does not confirm or change video detections, reviews, or reliability metrics."
        actions={
          <Link className="button button--secondary" to="/system">
            Back to sources
          </Link>
        }
      />
      {source.isLoading ? <p role="status">Loading source configuration…</p> : null}
      {source.isError ? (
        <Surface>
          <h2>Source configuration could not be loaded</h2>
          <p>{source.error.message}</p>
        </Surface>
      ) : null}
      {source.isSuccess ? (
        <Surface>
          <h2>{source.data.name}</h2>
          <p>
            Approved area: {source.data.context_area_label ?? 'not configured'} · Context retrieval:{' '}
            {source.data.context_retrieval_enabled ? 'enabled' : 'disabled'}
          </p>
        </Surface>
      ) : null}
      {canRefresh && source.data?.context_retrieval_enabled ? (
        <Surface>
          <h2>Refresh public context</h2>
          <p>
            Uses the source’s approved coarse area and configured topics for a bounded 24-hour
            search.
          </p>
          <button
            className="button button--primary"
            disabled={
              refresh.isPending || job.data?.status === 'pending' || job.data?.status === 'running'
            }
            onClick={() => refresh.mutate()}
          >
            {refresh.isPending ? 'Queueing…' : 'Queue refresh'}
          </button>
          {refresh.isError ? <p role="alert">{refresh.error.message}</p> : null}
          {jobId ? (
            <p role="status">
              Refresh job {job.data?.status ?? 'queued'}
              {job.isError ? ' · status unavailable' : ''}
            </p>
          ) : null}
        </Surface>
      ) : null}
      {canRefresh && source.isSuccess && !source.data.context_retrieval_enabled ? (
        <Surface>
          <p>Public context refresh is disabled for this source.</p>
        </Surface>
      ) : null}
      {contextItems.isLoading ? <p role="status">Loading attributed context…</p> : null}
      {contextItems.isError ? (
        <Surface>
          <h2>Context could not be loaded</h2>
          <p>{contextItems.error.message}</p>
          <button className="button button--primary" onClick={() => void contextItems.refetch()}>
            Retry
          </button>
        </Surface>
      ) : null}
      {contextItems.isSuccess && contextItems.data.items.length === 0 ? (
        <Surface>
          <h2>No saved public context</h2>
          <p>No context results have been saved. This does not mean an area is safe.</p>
        </Surface>
      ) : null}
      {contextItems.isSuccess && contextItems.data.items.length > 0 ? (
        <div className="context-results">
          {contextItems.data.items.map((item) => (
            <Surface key={item.id}>
              <div className="section-heading">
                <h2>{item.title}</h2>
                <StatusBadge tone={item.freshness_status === 'current' ? 'success' : 'neutral'}>
                  {item.freshness_status}
                </StatusBadge>
              </div>
              <p>{item.summary}</p>
              <p>
                {item.topic.replaceAll('_', ' ')} · {item.publisher ?? item.source_domain} ·{' '}
                {item.source_domain}
              </p>
              <p>
                Published:{' '}
                {item.published_at ? new Date(item.published_at).toLocaleString() : 'not provided'}
                {' · '}Retrieved: {new Date(item.retrieved_at).toLocaleString()}
              </p>
              <a href={item.source_url} target="_blank" rel="noreferrer">
                Open public source
              </a>
            </Surface>
          ))}
        </div>
      ) : null}
    </div>
  );
}
