import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Navigate } from 'react-router-dom';

import { ApiError, requestJson, type CurrentUser } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { Surface } from '../components/Surface';

type PublicContextResult = {
  title: string;
  snippet: string;
  publisher: string | null;
  source_domain: string;
  source_url: string;
  published_at: string | null;
  retrieved_at: string;
  freshness: 'current' | 'stale' | 'unknown';
};

type SearchResponse = {
  status: 'available' | 'empty';
  results: PublicContextResult[];
  note: string;
};

type FetchResponse = {
  title: string;
  description: string | null;
  text: string;
  publisher: string;
  source_domain: string;
  source_url: string;
  published_at: string | null;
  retrieved_at: string;
  freshness: 'current' | 'stale' | 'unknown';
};

const topics = [
  'weather_advisory',
  'transport_disruption',
  'public_notice',
  'public_event',
  'emergency_advisory',
  'other',
] as const;

export function PublicContextPage() {
  const [query, setQuery] = useState('');
  const [topic, setTopic] = useState<(typeof topics)[number]>('public_notice');
  const user = useQuery({
    queryKey: ['current-user'],
    queryFn: () => requestJson<CurrentUser>('/auth/me'),
    retry: false,
  });
  const search = useMutation({
    mutationFn: () =>
      requestJson<SearchResponse>('/public-context/search', {
        method: 'POST',
        body: JSON.stringify({ query, topic }),
      }),
  });
  const fetchPage = useMutation({
    mutationFn: (source_url: string) =>
      requestJson<FetchResponse>('/public-context/fetch', {
        method: 'POST',
        body: JSON.stringify({ source_url }),
      }),
  });
  if (user.isLoading) return <p role="status">Checking your session…</p>;
  if (user.error instanceof ApiError && user.error.status === 401)
    return <Navigate to="/login" replace />;
  if (user.isError) return <p role="alert">Your session could not be checked. Sign in again.</p>;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="External public sources"
        title="Public context search"
        description="Search approved public sources for situational context. Results are external information, not evidence that a video event occurred."
      />
      <Surface>
        <form
          className="context-search-form"
          onSubmit={(event) => {
            event.preventDefault();
            search.mutate();
          }}
        >
          <label>
            Public query
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              minLength={3}
              maxLength={240}
              required
              autoComplete="off"
              placeholder="For example: city rain advisory"
            />
          </label>
          <label>
            Context topic
            <select
              value={topic}
              onChange={(event) => setTopic(event.target.value as typeof topic)}
            >
              {topics.map((item) => (
                <option key={item} value={item}>
                  {item.replaceAll('_', ' ')}
                </option>
              ))}
            </select>
          </label>
          <button className="button button--primary" disabled={search.isPending} type="submit">
            {search.isPending ? 'Searching…' : 'Search public sources'}
          </button>
        </form>
        {search.isPending ? <p role="status">Searching approved public domains…</p> : null}
        {search.isError ? (
          <p role="alert">
            {search.error instanceof ApiError && search.error.status === 429
              ? 'Please wait before starting another search.'
              : 'Public context is currently unavailable. Incident review and evidence access remain available.'}
          </p>
        ) : null}
      </Surface>
      {search.isSuccess && search.data.results.length === 0 ? (
        <Surface>
          <h2>No public results returned</h2>
          <p>
            This means the search returned no matching public pages. It does not mean an area is
            safe.
          </p>
        </Surface>
      ) : null}
      {search.isSuccess && search.data.results.length > 0 ? (
        <div className="context-results">
          {search.data.results.map((result) => (
            <Surface key={`${result.source_url}-${result.retrieved_at}`}>
              <div className="section-heading">
                <h2>{result.title}</h2>
                <StatusBadge tone={result.freshness === 'current' ? 'success' : 'neutral'}>
                  {result.freshness}
                </StatusBadge>
              </div>
              <p>{result.snippet || 'No excerpt was provided by the search provider.'}</p>
              <p>
                {result.publisher ?? result.source_domain} · {result.source_domain}
              </p>
              <p>
                Published:{' '}
                {result.published_at
                  ? new Date(result.published_at).toLocaleString()
                  : 'not provided'}
                {' · '}Retrieved: {new Date(result.retrieved_at).toLocaleString()}
              </p>
              <a href={result.source_url} target="_blank" rel="noreferrer">
                Open public source
              </a>
              <button
                className="button button--secondary"
                disabled={fetchPage.isPending}
                onClick={() => fetchPage.mutate(result.source_url)}
                type="button"
              >
                {fetchPage.isPending && fetchPage.variables === result.source_url
                  ? 'Fetching…'
                  : 'Fetch bounded page excerpt'}
              </button>
              {fetchPage.isError && fetchPage.variables === result.source_url ? (
                <p role="alert">The public page could not be fetched or did not pass validation.</p>
              ) : null}
              {fetchPage.isSuccess && fetchPage.variables === result.source_url ? (
                <div className="context-excerpt" aria-live="polite">
                  <h3>{fetchPage.data.title}</h3>
                  <p>{fetchPage.data.description ?? 'No description was provided.'}</p>
                  <p>
                    Retrieved {new Date(fetchPage.data.retrieved_at).toLocaleString()} ·{' '}
                    {fetchPage.data.freshness}
                  </p>
                  <pre>{fetchPage.data.text}</pre>
                </div>
              ) : null}
            </Surface>
          ))}
        </div>
      ) : null}
      {search.isSuccess ? <p role="note">{search.data.note}</p> : null}
    </div>
  );
}
