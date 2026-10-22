import { render, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { AppShell } from './AppShell';

describe('AppShell', () => {
  it('exposes a skip link and labelled primary navigation destinations', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/" element={<h1>Workspace content</h1>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByRole('link', { name: 'Skip to content' })).toHaveAttribute(
      'href',
      '#main-content',
    );
    const navigation = screen.getByRole('navigation', { name: 'Primary navigation' });
    const links = within(navigation).getAllByRole('link');
    expect(links.map((link) => link.textContent)).toEqual([
      'Dashboard',
      'Candidate events',
      'Reliability',
      'Evaluations',
      'Public context',
      'System',
      'Sign in',
    ]);
    expect(screen.getByRole('heading', { name: 'Workspace content' })).toBeInTheDocument();
  });
});
