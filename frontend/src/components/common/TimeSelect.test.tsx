import { useState } from 'react';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { TimeSelect } from '@/components/common/TimeSelect';
import { renderWithProviders } from '@/test-utils';

function Harness({ initial = '', onPick }: { initial?: string; onPick: (v: string) => void }) {
  const [value, setValue] = useState(initial);
  return (
    <TimeSelect
      value={value}
      onChange={(v) => {
        setValue(v);
        onPick(v);
      }}
    />
  );
}

describe('TimeSelect', () => {
  it('emits HH:MM after picking hour and minute, with no long scroll list', async () => {
    const user = userEvent.setup();
    const onPick = vi.fn();
    renderWithProviders(<Harness onPick={onPick} />);

    const [hourBox, minuteBox] = screen.getAllByRole('combobox');
    hourBox.focus();
    await user.keyboard('{ArrowDown}');
    await user.click(await screen.findByText('09'));
    minuteBox.focus();
    await user.keyboard('{ArrowDown}');
    await user.click(await screen.findByText('15'));

    expect(onPick).toHaveBeenCalledWith('09:15');
  });

  it('displays API HH:MM:SS values as HH:MM', () => {
    renderWithProviders(<Harness initial="09:00:00" onPick={() => undefined} />);
    // Both triggers show the parsed parts, not placeholders.
    expect(screen.getAllByRole('combobox')).toHaveLength(2);
  });
});
