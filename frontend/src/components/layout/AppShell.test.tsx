import '@/test-utils';
import { screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { AuthProvider } from '@/auth/AuthContext';
import { AppShell } from '@/components/layout/AppShell';
import { ADMIN_USER, STUDENT_USER, mockUserStore } from '@/test-utils';

function renderShell() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 } },
  });
  localStorage.setItem('ttg_access_token', 'test-token');
  render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter initialEntries={['/']}>
          <Routes>
            <Route element={<AppShell />}>
              <Route index element={<div>CONTENT</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe('AppShell navigation', () => {
  it('shows admin sections including Generate for admins', async () => {
    mockUserStore.user = ADMIN_USER;
    renderShell();
    expect(await screen.findByText('Generate')).toBeInTheDocument();
    expect(screen.getByText('Availability')).toBeInTheDocument();
    expect(screen.getByText('Requirements')).toBeInTheDocument();
    expect(screen.getByText('ADMIN')).toBeInTheDocument();
  });

  it('shows only student sections for students', async () => {
    mockUserStore.user = STUDENT_USER;
    renderShell();
    expect(await screen.findByText('My Timetable')).toBeInTheDocument();
    expect(screen.queryByText('Generate')).not.toBeInTheDocument();
    expect(screen.queryByText('Availability')).not.toBeInTheDocument();
    expect(screen.getByText('STUDENT')).toBeInTheDocument();
  });
});
