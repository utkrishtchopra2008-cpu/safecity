import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { IncidentsPage } from './IncidentsPage';

function jsonResponse(payload: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    }),
  );
}

describe('IncidentsPage', () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it('applies the documented filters and navigates bounded pages', async () => {
    const requestedUrls: URL[] = [];
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = new URL(String(input), 'http://testserver');
      if (url.pathname.endsWith('/auth/me'))
        return jsonResponse({
          id: 'user-1',
          display_name: 'Operator',
          email: 'operator@example.test',
          role: 'operator',
          is_active: true,
        });
      if (url.pathname.endsWith('/incidents')) {
        requestedUrls.push(url);
        const page = Number(url.searchParams.get('page'));
        return jsonResponse({
          items: [
            {
              id: `event-${page}`,
              source_id: 'source-12345678',
              event_start_at: '2026-10-20T10:00:00Z',
              event_end_at: null,
              received_at: '2026-10-20T10:01:00Z',
              detection_category: 'vehicle_observation',
              detector_name: 'demo',
              detector_version: null,
              detector_score: null,
              score_semantics: null,
              review_status: 'unreviewed',
            },
          ],
          page,
          page_size: Number(url.searchParams.get('page_size')),
          has_more: page === 1,
          total_count: 2,
        });
      }
      return Promise.reject(new Error(`Unexpected request ${url}`));
    });
    vi.stubGlobal('fetch', fetchMock);
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <IncidentsPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await screen.findByRole('link', { name: 'vehicle_observation' });
    fireEvent.change(screen.getByLabelText('Start time'), {
      target: { value: '2026-10-20T09:00' },
    });
    fireEvent.change(screen.getByLabelText('End time'), {
      target: { value: '2026-10-20T11:00' },
    });
    fireEvent.change(screen.getByRole('textbox', { name: 'Source ID' }), {
      target: { value: 'source-12345678' },
    });
    fireEvent.change(screen.getByLabelText('Observation category'), {
      target: { value: 'vehicle_observation' },
    });
    fireEvent.change(screen.getByLabelText('Review status'), {
      target: { value: 'unreviewed' },
    });
    fireEvent.change(screen.getByLabelText('Sort by'), {
      target: { value: 'event_start_at' },
    });
    fireEvent.change(screen.getByLabelText('Sort order'), {
      target: { value: 'asc' },
    });
    fireEvent.change(screen.getByLabelText('Rows per page'), {
      target: { value: '50' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Apply filters' }));

    await waitFor(() => expect(requestedUrls.length).toBeGreaterThanOrEqual(3));
    const filtered = requestedUrls.find((url) => url.searchParams.get('detection_category'));
    expect(filtered).toBeDefined();
    expect(filtered?.searchParams.get('start_at')).toBe(new Date('2026-10-20T09:00').toISOString());
    expect(filtered?.searchParams.get('end_at')).toBe(new Date('2026-10-20T11:00').toISOString());
    expect(filtered?.searchParams.get('source_id')).toBe('source-12345678');
    expect(filtered?.searchParams.get('review_status')).toBe('unreviewed');
    expect(filtered?.searchParams.get('sort_by')).toBe('event_start_at');
    expect(filtered?.searchParams.get('sort_order')).toBe('asc');
    expect(filtered?.searchParams.get('page_size')).toBe('50');

    await screen.findByRole('button', { name: 'Next page' });
    fireEvent.click(screen.getByRole('button', { name: 'Next page' }));
    await waitFor(() =>
      expect(
        requestedUrls.some(
          (url) =>
            url.searchParams.get('page') === '2' &&
            url.searchParams.get('detection_category') === 'vehicle_observation',
        ),
      ).toBe(true),
    );
    expect(await screen.findByText('Page 2 · Showing 1 of 2 records.')).toBeInTheDocument();
  });

  it('prevents applying an inverted time range', async () => {
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
      if (url.includes('/incidents?'))
        return jsonResponse({ items: [], page: 1, page_size: 25, has_more: false, total_count: 0 });
      return Promise.reject(new Error(`Unexpected request ${url}`));
    });
    vi.stubGlobal('fetch', fetchMock);
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <IncidentsPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await screen.findByText('No candidate events yet');
    fireEvent.change(screen.getByLabelText('Start time'), {
      target: { value: '2026-10-20T12:00' },
    });
    fireEvent.change(screen.getByLabelText('End time'), {
      target: { value: '2026-10-20T10:00' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Apply filters' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The start time must be before or equal to the end time.',
    );
  });
});
