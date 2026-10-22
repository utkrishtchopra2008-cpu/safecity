import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { SetupStatusPage } from './SetupStatusPage';

describe('SetupStatusPage', () => {
  it('communicates implemented and unavailable capability without claiming completion', () => {
    render(
      <MemoryRouter>
        <SetupStatusPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole('heading', { name: 'Implementation status' })).toBeInTheDocument();
    expect(screen.getByText('Partial implementation')).toBeInTheDocument();
    expect(screen.getByText('Queued only')).toBeInTheDocument();
    expect(screen.getByText('Unavailable')).toBeInTheDocument();
    expect(screen.getByText('TinyFish — disabled')).toBeInTheDocument();
    expect(screen.getByText('No video source connected')).toBeInTheDocument();
  });
});
