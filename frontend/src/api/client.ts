export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/+$/, '');
let csrfToken: string | undefined;

type ApiProblem = {
  code?: string;
  title?: string;
  detail?: string;
  message?: string;
  request_id?: string;
};

export type CurrentUser = {
  id: string;
  display_name: string;
  email: string;
  role: 'operator' | 'supervisor' | 'technical_admin';
  is_active: boolean;
};

export type IncidentItem = {
  id: string;
  source_id: string;
  event_start_at: string | null;
  event_end_at: string | null;
  received_at: string;
  detection_category: string;
  detector_name: string;
  detector_version: string | null;
  detector_score: number | null;
  score_semantics: string | null;
  review_status: 'unreviewed' | 'reviewed';
};

export type IncidentPage = {
  items: IncidentItem[];
  page: number;
  page_size: number;
  has_more: boolean;
  total_count: number;
};

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId?: string;

  constructor(status: number, code: string, message: string, requestId?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }
}

function isJsonContentType(contentType: string | null): boolean {
  return (
    contentType !== null &&
    (contentType.includes('application/json') || contentType.includes('+json'))
  );
}

async function readProblem(response: Response): Promise<ApiProblem> {
  if (!isJsonContentType(response.headers.get('content-type'))) return {};
  try {
    const payload: unknown = await response.json();
    if (typeof payload !== 'object' || payload === null) return {};
    const candidate = payload as Record<string, unknown>;
    return {
      code: typeof candidate.code === 'string' ? candidate.code : undefined,
      title: typeof candidate.title === 'string' ? candidate.title : undefined,
      detail: typeof candidate.detail === 'string' ? candidate.detail : undefined,
      message: typeof candidate.message === 'string' ? candidate.message : undefined,
      request_id: typeof candidate.request_id === 'string' ? candidate.request_id : undefined,
    };
  } catch {
    return {};
  }
}

export async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const method = (init.method || 'GET').toUpperCase();
  const headers = new Headers(init.headers);
  headers.set('Accept', 'application/json');
  if (init.body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const isLogin = normalizedPath === '/auth/login' && method === 'POST';
  if (isLogin) csrfToken = undefined;

  if (!['GET', 'HEAD', 'OPTIONS'].includes(method) && !isLogin) {
    csrfToken ||= await getCsrfToken();
    headers.set('X-CSRF-Token', csrfToken);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${normalizedPath}`, {
      ...init,
      headers,
      credentials: 'include',
    });
  } catch {
    throw new ApiError(
      0,
      'NETWORK_ERROR',
      'The API could not be reached. Check the connection and retry.',
    );
  }

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) csrfToken = undefined;
    const problem = await readProblem(response);
    throw new ApiError(
      response.status,
      problem.code || 'REQUEST_FAILED',
      problem.detail || problem.message || problem.title || 'The request could not be completed.',
      problem.request_id,
    );
  }

  if (isLogin || normalizedPath === '/auth/logout') csrfToken = undefined;

  if (response.status === 204) return undefined as T;
  if (!isJsonContentType(response.headers.get('content-type'))) {
    throw new ApiError(
      response.status,
      'UNEXPECTED_RESPONSE',
      'The API returned an unexpected response format.',
    );
  }

  return (await response.json()) as T;
}

async function getCsrfToken(): Promise<string> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/auth/csrf`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      credentials: 'include',
    });
  } catch {
    throw new ApiError(
      0,
      'NETWORK_ERROR',
      'The API could not be reached. Check the connection and retry.',
    );
  }
  if (!response.ok) {
    csrfToken = undefined;
    const problem = await readProblem(response);
    throw new ApiError(
      response.status,
      problem.code || 'REQUEST_FAILED',
      problem.detail || problem.title || 'The request could not be completed.',
      problem.request_id,
    );
  }
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new ApiError(200, 'UNEXPECTED_RESPONSE', 'The API returned an invalid CSRF response.');
  }
  if (typeof payload !== 'object' || payload === null || !('csrf_token' in payload)) {
    throw new ApiError(200, 'UNEXPECTED_RESPONSE', 'The API returned an invalid CSRF response.');
  }
  const token = (payload as { csrf_token?: unknown }).csrf_token;
  if (typeof token !== 'string' || token.length === 0) {
    throw new ApiError(200, 'UNEXPECTED_RESPONSE', 'The API returned an invalid CSRF response.');
  }
  return token;
}
