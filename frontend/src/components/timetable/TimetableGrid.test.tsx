import '@/test-utils';
import { renderWithProviders } from '@/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TimetableGrid } from '@/components/timetable/TimetableGrid';
import type { PeriodBrief, TimetableEntry } from '@/types/api';

const periods: PeriodBrief[] = [
  { id: 'p1', day_of_week: 'MONDAY', start_time: '09:00:00', end_time: '10:00:00', period_order: 1, is_break: false },
  { id: 'p2', day_of_week: 'MONDAY', start_time: '10:00:00', end_time: '11:00:00', period_order: 2, is_break: false },
  { id: 'p3', day_of_week: 'TUESDAY', start_time: '09:00:00', end_time: '10:00:00', period_order: 1, is_break: false },
];

const entry: TimetableEntry = {
  id: 'e1',
  timetable_id: 't1',
  division_code: 'CSE-A',
  subject_id: 's1',
  subject_code: 'CS201',
  subject_name: 'Databases',
  faculty_id: 'f1',
  faculty_name: 'Dr. Rao',
  room_id: 'r1',
  room_name: 'R-101',
  period: periods[0],
};

describe('TimetableGrid', () => {
  it('places entries in the right day/time cells', () => {
    renderWithProviders(<TimetableGrid periods={periods} entries={[entry]} />);
    expect(screen.getByText('Monday')).toBeInTheDocument();
    expect(screen.getByText('Tuesday')).toBeInTheDocument();
    expect(screen.getByText(/CS201/)).toBeInTheDocument();
    expect(screen.getByText('Dr. Rao')).toBeInTheDocument();
    expect(screen.getByText('R-101')).toBeInTheDocument();
  });

  it('shows an add affordance for empty cells in edit mode', async () => {
    const onAdd = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(
      <TimetableGrid periods={periods} entries={[entry]} editable onAdd={onAdd} />,
    );
    const buttons = screen.getAllByRole('button', { name: /add class/i });
    // 3 slots - 1 filled = 2 empty cells
    expect(buttons).toHaveLength(2);
    await user.click(buttons[0]);
    expect(onAdd).toHaveBeenCalledTimes(1);
  });

  it('calls onEdit when a filled cell is clicked in edit mode', async () => {
    const onEdit = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(
      <TimetableGrid periods={periods} entries={[entry]} editable onEdit={onEdit} />,
    );
    await user.click(screen.getByText(/CS201/));
    expect(onEdit).toHaveBeenCalledWith(entry);
  });

  it('shows an empty message when no periods exist', () => {
    renderWithProviders(<TimetableGrid periods={[]} entries={[]} />);
    expect(screen.getByText(/no periods configured/i)).toBeInTheDocument();
  });
});
