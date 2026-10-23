import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { DashboardPage } from './DashboardPage';

function jsonResponse(payload: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    }),
  );
}

describe('DashboardPage', () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it('sends the selected date and source filters to the summary API', async () => {
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
      if (url.pathname.endsWith('/dashboard/summary')) {
        requestedUrls.push(url);
        return jsonResponse({
          period_label: url.searchParams.has('start_at')
            ? 'custom period'
            : 'all available records',
          period_start: url.searchParams.get('start_at'),
          period_end: url.searchParams.get('end_at'),
          incident_counts: { unreviewed: 0, reviewed: 0 },
          recent_incidents: [],
          source_counts: {},
          job_counts: {},
          reliability_metrics_available: false,
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
          <DashboardPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await screen.findByText(/all available records/);
    fireEvent.change(screen.getByLabelText('Start time'), {
      target: { value: '2026-10-20T09:00' },
    });
    fireEvent.change(screen.getByLabelText('End time'), {
      target: { value: '2026-10-20T11:00' },
    });
    fireEvent.change(screen.getByRole('textbox', { name: 'Source ID' }), {
      target: { value: 'source-12345678' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Apply filters' }));

    await waitFor(() => expect(requestedUrls.length).toBe(2));
    const filtered = requestedUrls[1];
    expect(filtered?.searchParams.get('start_at')).toBe(new Date('2026-10-20T09:00').toISOString());
    expect(filtered?.searchParams.get('end_at')).toBe(new Date('2026-10-20T11:00').toISOString());
    expect(filtered?.searchParams.get('source_id')).toBe('source-12345678');
  });

  it('rejects an inverted date range without issuing a filtered request', async () => {
    const requestedUrls: string[] = [];
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
      if (url.includes('/dashboard/summary')) {
        requestedUrls.push(url);
        return jsonResponse({
          period_label: 'all available records',
          period_start: null,
          period_end: null,
          incident_counts: { unreviewed: 0, reviewed: 0 },
          recent_incidents: [],
          source_counts: {},
          job_counts: {},
          reliability_metrics_available: false,
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
          <DashboardPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await screen.findByText(/all available records/);
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
    expect(requestedUrls).toHaveLength(1);
  });
});
