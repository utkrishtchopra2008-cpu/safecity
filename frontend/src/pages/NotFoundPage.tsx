import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <section className="not-found" aria-labelledby="not-found-title">
      <p className="eyebrow">404 · Page not found</p>
      <h1 id="not-found-title">This route does not exist yet.</h1>
      <p>The requested path is not part of the current project foundation.</p>
      <Link className="button button--primary" to="/">Return to foundation</Link>
    </section>
  );
}
