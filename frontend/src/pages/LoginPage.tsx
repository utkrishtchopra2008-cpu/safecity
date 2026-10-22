import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';

import { ApiError, requestJson, type CurrentUser } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { Surface } from '../components/Surface';

export function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setBusy(true);
    try {
      await requestJson<{ user: CurrentUser }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      navigate('/incidents', { replace: true });
    } catch (cause) {
      setError(
        cause instanceof ApiError && cause.status === 401
          ? 'Email or password is incorrect. Check your details and try again.'
          : cause instanceof Error
            ? cause.message
            : 'Sign-in could not be completed. Try again.',
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-stack login-page">
      <PageHeader
        eyebrow="Authorized access"
        title="Sign in to SafeCity AI"
        description="Use your organization account to review candidate events and their evidence."
      />
      <Surface>
        <form className="form-stack" onSubmit={submit}>
          <label>
            Email address
            <input
              autoComplete="username"
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label>
            Password
            <input
              autoComplete="current-password"
              type="password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {error ? (
            <p className="form-error" role="alert">
              {error}
            </p>
          ) : null}
          <button className="button button--primary" type="submit" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </Surface>
    </div>
  );
}
