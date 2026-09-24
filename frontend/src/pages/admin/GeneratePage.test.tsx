import '@/test-utils';
import { ADMIN_USER, renderWithProviders } from '@/test-utils';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import GeneratePage from '@/pages/admin/GeneratePage';

vi.mock('@/services/timetableApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/timetableApi')>();
  return { ...actual, timetableApi: { ...actual.timetableApi, generate: vi.fn() } };
});

vi.mock('@/components/common/OptionSelect', () => ({
  OptionSelect: ({
    kind,
    value,
    onChange,
  }: {
    kind: string;
    value?: string;
    onChange: (v: string | undefined) => void;
  }) => (
    <select
      aria-label={`${kind}-select`}
      value={value ?? ''}
      onChange={(e) => onChange(e.target.value || undefined)}
    >
      <option value="">--</option>
      {kind === 'sessions' && <option value="sess-1">2026-27</option>}
      {kind === 'divisions' && <option value="div-1">CSE-A</option>}
    </select>
  ),
}));

import { timetableApi } from '@/services/timetableApi';

const mockedGenerate = vi.mocked(timetableApi.generate);

describe('GeneratePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  async function fillAndSubmit(user: ReturnType<typeof userEvent.setup>) {
    renderWithProviders(<GeneratePage />, { user: ADMIN_USER });
    await user.selectOptions(screen.getByLabelText('sessions-select'), 'sess-1');
    await user.selectOptions(screen.getByLabelText('divisions-select'), 'div-1');
    await user.click(screen.getByRole('button', { name: /generate timetable/i }));
  }

  it('shows the solver result on success', async () => {
    mockedGenerate.mockResolvedValueOnce({
      status: 'SUCCESS',
      timetable_id: 'tt-1',
      solver_status: 'OPTIMAL',
      objective_score: 218,
      generation_duration_ms: 842,
      warnings: [],
    });
    const user = userEvent.setup();
    await fillAndSubmit(user);
    await waitFor(() => {
      expect(screen.getByText(/timetable generated/i)).toBeInTheDocument();
    });
    expect(screen.getByText('OPTIMAL')).toBeInTheDocument();
    expect(screen.getByText('218')).toBeInTheDocument();
    expect(mockedGenerate).toHaveBeenCalledTimes(1);
  });

  it('shows conflicts and suggestions on infeasible generation', async () => {
    mockedGenerate.mockResolvedValueOnce({
      status: 'INFEASIBLE',
      solver_status: 'INFEASIBLE',
      conflicts: [
        {
          type: 'ROOM_UNAVAILABLE',
          severity: 'ERROR',
          message: 'No suitable laboratory is available.',
          subject: 'Physics Lab',
          division: 'CSE-A',
          details: {},
          suggestions: ['Add another suitable laboratory'],
        },
      ],
      suggestions: ['Add another suitable laboratory'],
      generation_duration_ms: 120,
    });
    const user = userEvent.setup();
    await fillAndSubmit(user);
    await waitFor(() => {
      expect(screen.getByText('ROOM_UNAVAILABLE')).toBeInTheDocument();
    });
    expect(screen.getByText(/no suitable laboratory/i)).toBeInTheDocument();
    expect(screen.getByText('Add another suitable laboratory')).toBeInTheDocument();
    expect(screen.queryByText(/timetable generated/i)).not.toBeInTheDocument();
  });
});
