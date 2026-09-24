import '@/test-utils';
import { ADMIN_USER, FACULTY_USER, renderWithProviders } from '@/test-utils';
import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { RequireRoles } from '@/components/layout/Guards';

describe('RequireRoles', () => {
  it('renders children for an allowed role', async () => {
    renderWithProviders(
      <RequireRoles roles={['ADMIN', 'SUPER_ADMIN']}>
        <div>SECRET ADMIN STUFF</div>
      </RequireRoles>,
      { user: ADMIN_USER, route: '/admin' },
    );
    expect(await screen.findByText('SECRET ADMIN STUFF')).toBeInTheDocument();
  });

  it('shows permission denied for a disallowed role', async () => {
    renderWithProviders(
      <RequireRoles roles={['ADMIN', 'SUPER_ADMIN']}>
        <div>SECRET ADMIN STUFF</div>
      </RequireRoles>,
      { user: FACULTY_USER, route: '/admin' },
    );
    expect(await screen.findByText(/permission denied/i)).toBeInTheDocument();
  });
});
