import { useQuery } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
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

type ReviewStatus = '' | 'unreviewed' | 'reviewed';
type SortField = 'received_at' | 'event_start_at' | 'detection_category' | 'review_status';
type SortOrder = 'asc' | 'desc';

type IncidentFilters = {
  startAt: string;
  endAt: string;
  sourceId: string;
  category: string;
  reviewStatus: ReviewStatus;
  sortBy: SortField;
  sortOrder: SortOrder;
};

const defaultFilters: IncidentFilters = {
  startAt: '',
  endAt: '',
  sourceId: '',
  category: '',
  reviewStatus: '',
  sortBy: 'received_at',
  sortOrder: 'desc',
};

function incidentQuery(page: number, pageSize: number, filters: IncidentFilters): string {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
    sort_by: filters.sortBy,
    sort_order: filters.sortOrder,
  });
  if (filters.startAt) params.set('start_at', new Date(filters.startAt).toISOString());
  if (filters.endAt) params.set('end_at', new Date(filters.endAt).toISOString());
  if (filters.sourceId.trim()) params.set('source_id', filters.sourceId.trim());
  if (filters.category.trim()) params.set('detection_category', filters.category.trim());
  if (filters.reviewStatus) params.set('review_status', filters.reviewStatus);
  return `/incidents?${params.toString()}`;
}

function useCurrentUser() {
  return useQuery({
    queryKey: ['current-user'],
    queryFn: () => requestJson<CurrentUser>('/auth/me'),
    retry: false,
  });
}

export function IncidentsPage() {
  const user = useCurrentUser();
  const [draftFilters, setDraftFilters] = useState<IncidentFilters>(defaultFilters);
  const [filters, setFilters] = useState<IncidentFilters>(defaultFilters);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [filterError, setFilterError] = useState<string | null>(null);
  const incidents = useQuery({
    queryKey: ['incidents', page, pageSize, filters],
    queryFn: () => requestJson<IncidentPageData>(incidentQuery(page, pageSize, filters)),
    enabled: user.isSuccess,
  });

  if (user.isLoading) return <p role="status">Checking your session…</p>;
  if (user.error instanceof ApiError && user.error.status === 401)
    return <Navigate to="/login" replace />;
  if (user.isError)
    return (
      <p role="alert">Your session could not be checked. Reload this page or sign in again.</p>
    );

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      draftFilters.startAt &&
      draftFilters.endAt &&
      new Date(draftFilters.startAt) > new Date(draftFilters.endAt)
    ) {
      setFilterError('The start time must be before or equal to the end time.');
      return;
    }
    setFilterError(null);
    setPage(1);
    setFilters(draftFilters);
  }

  function clearFilters() {
    setFilterError(null);
    setDraftFilters(defaultFilters);
    setFilters(defaultFilters);
    setPage(1);
  }

  const hasAppliedFilters = Object.entries(filters).some(([key, value]) =>
    key === 'sortBy'
      ? value !== 'received_at'
      : key === 'sortOrder'
        ? value !== 'desc'
        : value !== '',
  );

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Operations"
        title="Candidate events"
        description="Review detector observations with their evidence. A candidate event is not a confirmed incident."
        actions={<StatusBadge tone="info">Live API</StatusBadge>}
      />
      <Surface>
        <h2 id="incident-filters-heading">Filter candidate events</h2>
        <p>Entered times use your local timezone and are sent to the API as UTC instants.</p>
        <form
          className="incident-filters"
          aria-labelledby="incident-filters-heading"
          onSubmit={applyFilters}
        >
          <label>
            Start time
            <input
              type="datetime-local"
              value={draftFilters.startAt}
              onChange={(event) =>
                setDraftFilters({ ...draftFilters, startAt: event.target.value })
              }
            />
          </label>
          <label>
            End time
            <input
              type="datetime-local"
              value={draftFilters.endAt}
              onChange={(event) => setDraftFilters({ ...draftFilters, endAt: event.target.value })}
            />
          </label>
          <label>
            Source ID
            <input
              type="text"
              aria-label="Source ID"
              autoComplete="off"
              spellCheck={false}
              aria-describedby="incident-source-help"
              value={draftFilters.sourceId}
              onChange={(event) =>
                setDraftFilters({ ...draftFilters, sourceId: event.target.value })
              }
            />
            <span className="field-help" id="incident-source-help">
              Optional source UUID
            </span>
          </label>
          <label>
            Observation category
            <input
              type="text"
              maxLength={120}
              value={draftFilters.category}
              onChange={(event) =>
                setDraftFilters({ ...draftFilters, category: event.target.value })
              }
            />
          </label>
          <label>
            Review status
            <select
              value={draftFilters.reviewStatus}
              onChange={(event) =>
                setDraftFilters({
                  ...draftFilters,
                  reviewStatus: event.target.value as ReviewStatus,
                })
              }
            >
              <option value="">All statuses</option>
              <option value="unreviewed">Unreviewed</option>
              <option value="reviewed">Reviewed</option>
            </select>
          </label>
          <label>
            Sort by
            <select
              value={draftFilters.sortBy}
              onChange={(event) =>
                setDraftFilters({ ...draftFilters, sortBy: event.target.value as SortField })
              }
            >
              <option value="received_at">Received time</option>
              <option value="event_start_at">Event time</option>
              <option value="detection_category">Observation category</option>
              <option value="review_status">Review status</option>
            </select>
          </label>
          <label>
            Sort order
            <select
              value={draftFilters.sortOrder}
              onChange={(event) =>
                setDraftFilters({ ...draftFilters, sortOrder: event.target.value as SortOrder })
              }
            >
              <option value="desc">Newest first</option>
              <option value="asc">Oldest first</option>
            </select>
          </label>
          <label>
            Rows per page
            <select
              value={pageSize}
              onChange={(event) => {
                setPageSize(Number(event.target.value));
                setPage(1);
              }}
            >
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </label>
          <div className="incident-filter-actions">
            <button className="button button--primary" type="submit">
              Apply filters
            </button>
            <button className="button button--secondary" onClick={clearFilters} type="button">
              Clear filters
            </button>
          </div>
        </form>
        {filterError ? <p role="alert">{filterError}</p> : null}
      </Surface>
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
          <h2>{hasAppliedFilters ? 'No events match these filters' : 'No candidate events yet'}</h2>
          <p>
            {hasAppliedFilters
              ? 'Adjust or clear the filters to see more candidate events.'
              : 'Events will appear here only when a configured processing workflow records them.'}
          </p>
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
          <div className="incident-pagination">
            <p className="surface-footnote">
              Page {incidents.data.page} · Showing {incidents.data.items.length} of{' '}
              {incidents.data.total_count} records.
            </p>
            <nav aria-label="Candidate event pages" className="incident-pagination-actions">
              <button
                className="button button--secondary"
                disabled={page <= 1 || incidents.isFetching}
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                type="button"
              >
                Previous page
              </button>
              <button
                className="button button--secondary"
                disabled={!incidents.data.has_more || incidents.isFetching}
                onClick={() => setPage((current) => current + 1)}
                type="button"
              >
                Next page
              </button>
            </nav>
          </div>
        </Surface>
      ) : null}
    </div>
  );
}
