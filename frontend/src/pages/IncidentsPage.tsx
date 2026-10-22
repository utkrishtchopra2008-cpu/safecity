import { useQuery } from '@tanstack/react-query';
import { Link, Navigate } from 'react-router-dom';

import {
  ApiError,
  requestJson,
  type CurrentUser,
  type IncidentPage as IncidentPageData,
} from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { Surface } from '../components/Surface';

function useCurrentUser() {
  return useQuery({
    queryKey: ['current-user'],
    queryFn: () => requestJson<CurrentUser>('/auth/me'),
    retry: false,
  });
}

export function IncidentsPage() {
  const user = useCurrentUser();
  const incidents = useQuery({
    queryKey: ['incidents', 1],
    queryFn: () => requestJson<IncidentPageData>('/incidents?page=1&page_size=25'),
    enabled: user.isSuccess,
  });

  if (user.isLoading) return <p role="status">Checking your session…</p>;
  if (user.error instanceof ApiError && user.error.status === 401)
    return <Navigate to="/login" replace />;
  if (user.isError)
    return (
      <p role="alert">Your session could not be checked. Reload this page or sign in again.</p>
    );

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Operations"
        title="Candidate events"
        description="Review detector observations with their evidence. A candidate event is not a confirmed incident."
        actions={<StatusBadge tone="info">Live API</StatusBadge>}
      />
      {incidents.isLoading ? <p role="status">Loading candidate events…</p> : null}
      {incidents.isError ? (
        <Surface>
          <h2>Events could not be loaded</h2>
          <p>
            {incidents.error instanceof Error ? incidents.error.message : 'The request failed.'}
          </p>
          <button className="button button--primary" onClick={() => void incidents.refetch()}>
            Retry
          </button>
        </Surface>
      ) : null}
      {incidents.isSuccess && incidents.data.items.length === 0 ? (
        <Surface>
          <h2>No candidate events yet</h2>
          <p>Events will appear here only when a configured processing workflow records them.</p>
        </Surface>
      ) : null}
      {incidents.isSuccess && incidents.data.items.length > 0 ? (
        <Surface className="table-surface">
          <div className="table-scroll" role="region" aria-label="Candidate events" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th scope="col">Received</th>
                  <th scope="col">Observation</th>
                  <th scope="col">Source</th>
                  <th scope="col">Review</th>
                </tr>
              </thead>
              <tbody>
                {incidents.data.items.map((item) => (
                  <tr key={item.id}>
                    <td>{new Date(item.received_at).toLocaleString()}</td>
                    <td>
                      <Link to={`/incidents/${item.id}`}>{item.detection_category}</Link>
                    </td>
                    <td>
                      <code>{item.source_id.slice(0, 8)}</code>
                    </td>
                    <td>
                      <StatusBadge tone={item.review_status === 'reviewed' ? 'success' : 'warning'}>
                        {item.review_status}
                      </StatusBadge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="surface-footnote">
            Showing {incidents.data.items.length} of {incidents.data.total_count} records.
          </p>
        </Surface>
      ) : null}
    </div>
  );
}
