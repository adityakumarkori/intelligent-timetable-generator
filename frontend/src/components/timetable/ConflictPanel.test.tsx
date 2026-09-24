import '@/test-utils';
import { renderWithProviders } from '@/test-utils';
import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import { ConflictPanel } from '@/components/timetable/ConflictPanel';
import type { Conflict } from '@/types/api';

const conflicts: Conflict[] = [
  {
    type: 'ROOM_UNAVAILABLE',
    severity: 'ERROR',
    message: 'No suitable laboratory is available in the remaining periods.',
    subject: 'Physics Lab',
    division: 'CSE-A',
    details: {},
    suggestions: ['Add another suitable laboratory', 'Increase available periods'],
  },
];

describe('ConflictPanel', () => {
  it('renders type, message, entities, and suggestions — never a bare failure', () => {
    renderWithProviders(<ConflictPanel conflicts={conflicts} />);
    expect(screen.queryByText(/^generation failed\.?$/i)).not.toBeInTheDocument();
    expect(screen.getByText('ROOM_UNAVAILABLE')).toBeInTheDocument();
    expect(screen.getByText(/no suitable laboratory/i)).toBeInTheDocument();
    expect(screen.getByText(/Subject: Physics Lab/)).toBeInTheDocument();
    expect(screen.getByText(/Division: CSE-A/)).toBeInTheDocument();
    expect(screen.getByText('Add another suitable laboratory')).toBeInTheDocument();
    expect(screen.getByText('Increase available periods')).toBeInTheDocument();
  });
});
