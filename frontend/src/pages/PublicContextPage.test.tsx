import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { PublicContextPage } from './PublicContextPage';

function jsonResponse(payload: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    }),
  );
}

describe('PublicContextPage', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('renders provider text as inert text, not executable markup', async () => {
    const snippet = '<img src=x onerror=alert(1)> public notice';
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/auth/me'))
        return jsonResponse({
          id: 'user-1',
          display_name: 'Operator',
          email: 'operator@example.test',
          role: 'operator',
          is_active: true,
        });
      if (url.endsWith('/auth/csrf')) return jsonResponse({ csrf_token: 'test-csrf' });
      if (url.endsWith('/public-context/search'))
        return jsonResponse({
          status: 'available',
          note: 'Public context does not verify a video incident.',
          results: [
            {
              title: 'Public notice',
              snippet,
              publisher: 'Example',
              source_domain: 'example.gov',
              source_url: 'https://example.gov/notice',
              published_at: null,
              retrieved_at: '2026-10-23T00:00:00Z',
              freshness: 'unknown',
            },
          ],
        });
      return Promise.reject(new Error(`Unexpected request ${url}`));
    });
    vi.stubGlobal('fetch', fetchMock);
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <PublicContextPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await screen.findByLabelText('Public query');
    fireEvent.change(screen.getByLabelText('Public query'), {
      target: { value: 'public city notice' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Search public sources' }));

    await waitFor(() => expect(screen.getByText(snippet)).toBeInTheDocument());
    expect(document.querySelector('img')).toBeNull();
  });
});
