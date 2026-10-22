import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { SourceAdminPanel } from './SourceAdminPanel';

function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <SourceAdminPanel />
    </QueryClientProvider>,
  );
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function sourceNameField(section: string) {
  const heading = screen.getByRole('heading', { name: section });
  return within(heading.parentElement as HTMLElement).getByLabelText('Source name');
}

describe('SourceAdminPanel', () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it('registers a simulated source and identifies it as DEMO', async () => {
    const fetchMock = vi.fn((...args: Parameters<typeof fetch>) => {
      const [input] = args;
      const url = String(input);
      if (url.endsWith('/auth/csrf'))
        return Promise.resolve(jsonResponse({ csrf_token: 'csrf-demo' }));
      if (url.endsWith('/sources')) {
        return Promise.resolve(
          jsonResponse(
            {
              id: 'source-demo',
              name: 'Demo source',
              source_type: 'simulated',
              status: 'ready',
              created_at: '2026-10-23T00:00:00Z',
              last_processed_at: null,
              context_area_label: null,
              context_retrieval_enabled: false,
            },
            201,
          ),
        );
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);
    const user = userEvent.setup();
    renderPanel();

    await user.type(sourceNameField('Register a simulated source'), 'Demo source');
    await user.click(screen.getByRole('button', { name: 'Register simulated source' }));

    expect(await screen.findByRole('status')).toHaveTextContent('DEMO source registered.');
    const registration = fetchMock.mock.calls.find(([url]) =>
      String(url).endsWith('/sources'),
    )?.[1];
    expect(JSON.parse(String(registration?.body))).toMatchObject({
      name: 'Demo source',
      source_type: 'simulated',
      context_retrieval_enabled: false,
    });
  });

  it('uploads a clip and labels processing observations as non-incident results', async () => {
    const fetchMock = vi.fn((...args: Parameters<typeof fetch>) => {
      const [input] = args;
      const url = String(input);
      if (url.endsWith('/auth/csrf'))
        return Promise.resolve(jsonResponse({ csrf_token: 'csrf-upload' }));
      if (url.endsWith('/sources/upload')) {
        return Promise.resolve(
          jsonResponse(
            {
              source_id: 'source-upload',
              evidence_id: 'evidence-upload',
              job_id: 'job-upload',
              status: 'pending',
            },
            202,
          ),
        );
      }
      if (url.endsWith('/jobs/job-upload')) {
        return Promise.resolve(
          jsonResponse({
            status: 'completed',
            error_code: null,
            result_metadata: {
              mean_luma_0_255: 42.5,
              mean_laplacian_variance: 13.2,
              incident_detector: 'not_implemented',
              object_observations: [{ class_name: 'person', sample_count: 1, mean_score: 0.91 }],
            },
          }),
        );
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);
    const user = userEvent.setup();
    renderPanel();

    await user.type(sourceNameField('Upload a prerecorded clip'), 'Test clip');
    const videoInput = screen.getByLabelText('Video file') as HTMLInputElement;
    fireEvent.change(videoInput, {
      target: { files: [new File(['video bytes'], 'clip.mp4', { type: 'video/mp4' })] },
    });
    expect(videoInput.files).toHaveLength(1);
    videoInput.required = false;
    await user.click(screen.getByRole('button', { name: 'Upload and queue processing' }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(await screen.findByText(/person: observed in 1 sampled frames/)).toBeInTheDocument();
    expect(screen.getByText('Event detection is not configured.')).toBeInTheDocument();
    expect(
      screen.getByText(/Object observations are not incident classifications/),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith('/jobs/job-upload'))).toBe(
        true,
      ),
    );
    const uploadRequest = fetchMock.mock.calls.find(([url]) =>
      String(url).endsWith('/sources/upload'),
    )?.[1];
    expect(uploadRequest?.body).toBeInstanceOf(FormData);
    expect(new Headers(uploadRequest?.headers).get('Content-Type')).toBeNull();
  });

  it('shows a safe storage-unavailable message when upload cannot start', async () => {
    const fetchMock = vi.fn((...args: Parameters<typeof fetch>) => {
      const [input] = args;
      const url = String(input);
      if (url.endsWith('/auth/csrf'))
        return Promise.resolve(jsonResponse({ csrf_token: 'csrf-unavailable' }));
      if (url.endsWith('/sources/upload')) {
        return Promise.resolve(
          jsonResponse(
            {
              code: 'DEPENDENCY_UNAVAILABLE',
              detail: 'DEPENDENCY_UNAVAILABLE',
              request_id: 'req-storage',
            },
            503,
          ),
        );
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);
    const user = userEvent.setup();
    renderPanel();

    await user.type(sourceNameField('Upload a prerecorded clip'), 'Test clip');
    const videoInput = screen.getByLabelText('Video file') as HTMLInputElement;
    fireEvent.change(videoInput, {
      target: { files: [new File(['video bytes'], 'clip.mp4', { type: 'video/mp4' })] },
    });
    expect(videoInput.files).toHaveLength(1);
    videoInput.required = false;
    await user.click(screen.getByRole('button', { name: 'Upload and queue processing' }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Private video storage is not configured for this deployment.',
    );
  });
});
