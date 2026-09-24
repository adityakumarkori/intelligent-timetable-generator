import { useState } from 'react';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { renderWithProviders } from '@/test-utils';

/** Regression: radix Select must stay interactive inside a modal Dialog.
 *  The modal dialog locks body pointer-events; the select dropdown portals
 *  to <body> and would otherwise be dead (no open / no item clicks). */
function DialogWithSelect({ onPick }: { onPick: (v: string) => void }) {
  const [open, setOpen] = useState(false);
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>Open form</Button>
      </DialogTrigger>
      <DialogContent>
        <Select onValueChange={onPick}>
          <SelectTrigger>
            <SelectValue placeholder="Pick one" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="a">Option A</SelectItem>
            <SelectItem value="b">Option B</SelectItem>
          </SelectContent>
        </Select>
      </DialogContent>
    </Dialog>
  );
}

describe('Select inside Dialog', () => {
  it('opens the dropdown and picks an item', async () => {
    const user = userEvent.setup();
    let picked: string | null = null;
    renderWithProviders(
      <DialogWithSelect
        onPick={(v) => {
          picked = v;
        }}
      />,
    );
    await user.click(screen.getByRole('button', { name: /open form/i }));
    const trigger = screen.getByRole('combobox');
    trigger.focus();
    await user.keyboard('{ArrowDown}');
    await user.click(await screen.findByText('Option A'));
    expect(picked).toBe('a');
  });
});
