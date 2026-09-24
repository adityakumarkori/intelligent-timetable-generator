import '@/test-utils';
import { renderWithProviders } from '@/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ValidationPanel } from '@/components/timetable/ValidationPanel';

describe('ValidationPanel', () => {
  it('shows the valid state with score', () => {
    renderWithProviders(
      <ValidationPanel
        result={{
          timetable_id: 't1',
          valid: true,
          violations: [],
          status: 'VALID',
          errors: [],
          warnings: ['Minor gap on Monday'],
          score: 218,
        }}
        onValidate={() => undefined}
      />,
    );
    expect(screen.getByText('Valid')).toBeInTheDocument();
    expect(screen.getByText(/Score: 218/)).toBeInTheDocument();
    expect(screen.getByText(/Minor gap on Monday/)).toBeInTheDocument();
  });

  it('lists violations grouped by type', () => {
    renderWithProviders(
      <ValidationPanel
        result={{
          timetable_id: 't1',
          valid: false,
          violations: [
            { type: 'FACULTY_CONFLICT', message: 'Dr. Rao teaches twice at 09:00', details: {} },
          ],
          status: 'INVALID',
          errors: [
            { type: 'FACULTY_CONFLICT', message: 'Dr. Rao teaches twice at 09:00', details: {} },
          ],
          warnings: [],
          score: null,
        }}
        onValidate={() => undefined}
      />,
    );
    expect(screen.getByText('Validation failed')).toBeInTheDocument();
    expect(screen.getByText('FACULTY_CONFLICT')).toBeInTheDocument();
    expect(screen.getByText(/teaches twice/i)).toBeInTheDocument();
  });

  it('calls onValidate when the button is clicked', async () => {
    const onValidate = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(<ValidationPanel result={null} onValidate={onValidate} />);
    await user.click(screen.getByRole('button', { name: /validate timetable/i }));
    expect(onValidate).toHaveBeenCalledTimes(1);
  });
});
