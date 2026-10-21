import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { SetupStatusPage } from './SetupStatusPage';

describe('SetupStatusPage', () => {
  it('communicates foundation-only scope and TinyFish default state', () => {
    render(
      <MemoryRouter>
        <SetupStatusPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole('heading', { name: 'Foundation is in place' })).toBeInTheDocument();
    expect(screen.getByText('TinyFish — disabled')).toBeInTheDocument();
    expect(screen.getByText('No video source connected')).toBeInTheDocument();
  });
});
