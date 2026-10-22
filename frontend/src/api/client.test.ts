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

  it('fetches and sends the CSRF token for state-changing requests', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ csrf_token: 'csrf-test-token' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ saved: true }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    vi.stubGlobal('fetch', fetchMock);

    await expect(
      requestJson<{ saved: boolean }>('/incidents/1/reviews', { method: 'POST', body: '{}' }),
    ).resolves.toEqual({ saved: true });

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      expect.stringMatching(/\/api\/v1\/auth\/csrf$/),
      expect.objectContaining({ method: 'GET', credentials: 'include' }),
    );
    expect(fetchMock.mock.calls[1]?.[1]).toEqual(
      expect.objectContaining({ headers: expect.any(Headers), credentials: 'include' }),
    );
    const requestHeaders = new Headers(fetchMock.mock.calls[1]?.[1]?.headers);
    expect(requestHeaders.get('X-CSRF-Token')).toBe('csrf-test-token');
  });

  it('does not request a CSRF token before login', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ user: { role: 'operator' } }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await requestJson('/auth/login', { method: 'POST', body: '{}' });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0]?.[0]).toMatch(/\/api\/v1\/auth\/login$/);
  });
});
