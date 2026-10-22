import { ShieldCheck } from 'lucide-react';
import { Link, Outlet } from 'react-router-dom';

export function AppShell() {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <header className="topbar">
        <Link className="brand" to="/" aria-label="SafeCity AI home">
          <span className="brand-mark" aria-hidden="true">
            <ShieldCheck size={22} strokeWidth={1.8} />
          </span>
          <span className="brand-copy">
            <span className="brand-name">SafeCity AI</span>
            <span className="brand-descriptor">Public safety intelligence</span>
          </span>
        </Link>
        <span className="environment-badge">FOUNDATION</span>
        <nav className="primary-nav" aria-label="Primary navigation">
          <Link to="/dashboard">Dashboard</Link>
          <Link to="/incidents">Candidate events</Link>
          <Link to="/reliability">Reliability</Link>
          <Link to="/evaluations">Evaluations</Link>
          <Link to="/public-context">Public context</Link>
          <Link to="/system">System</Link>
          <Link to="/login">Sign in</Link>
        </nav>
      </header>
      <main id="main-content" className="main-content" tabIndex={-1}>
        <Outlet />
      </main>
      <footer className="app-footer">
        <span>
          Evidence first. Uncertainty is explicit. People remain responsible for decisions.
        </span>
      </footer>
    </div>
  );
}
