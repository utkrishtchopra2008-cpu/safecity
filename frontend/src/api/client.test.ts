import { afterEach, describe, expect, it, vi } from 'vitest';

import { requestJson } from './client';

describe('requestJson', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('returns JSON and always includes credentials for server-managed sessions', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: 'alive' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(requestJson<{ status: string }>('/test-resource')).resolves.toEqual({
      status: 'alive',
    });
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/v1\/test-resource$/),
      expect.objectContaining({ credentials: 'include' }),
    );
  });

  it('translates a structured error into an ApiError without leaking raw payloads', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            code: 'DEPENDENCY_UNAVAILABLE',
            detail: 'Try again later.',
            request_id: 'req-test',
          }),
          {
            status: 503,
            headers: { 'Content-Type': 'application/problem+json' },
          },
        ),
      ),
    );

    await expect(requestJson('/status')).rejects.toMatchObject({
      name: 'ApiError',
      status: 503,
      code: 'DEPENDENCY_UNAVAILABLE',
      message: 'Try again later.',
      requestId: 'req-test',
    });
  });

  it('reports network errors with a stable code', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('internal mock detail')));

    await expect(requestJson('/status')).rejects.toMatchObject({
      name: 'ApiError',
      status: 0,
      code: 'NETWORK_ERROR',
    });
  });
});
