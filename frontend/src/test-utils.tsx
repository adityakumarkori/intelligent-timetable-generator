import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, type RenderOptions } from '@testing-library/react';
import type { ReactElement } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { TooltipProvider } from '@radix-ui/react-tooltip';
import { vi } from 'vitest';
import { AuthProvider } from '@/auth/AuthContext';
import type { User } from '@/types/api';

export const ADMIN_USER: User = {
  id: '00000000-0000-0000-0000-000000000001',
  name: 'Admin',
  email: 'admin@college.edu',
  role: 'ADMIN',
  is_active: true,
};

export const FACULTY_USER: User = {
  ...ADMIN_USER,
  id: '00000000-0000-0000-0000-000000000002',
  name: 'Fac',
  email: 'f@x.edu',
  role: 'FACULTY',
};

export const STUDENT_USER: User = {
  ...ADMIN_USER,
  id: '00000000-0000-0000-0000-000000000003',
  name: 'Stu',
  email: 's@x.edu',
  role: 'STUDENT',
};

/** Mutable session user backing the authApi mock below. */
export const mockUserStore: { user: User | null } = { user: ADMIN_USER };

vi.mock('@/services/authApi', () => ({
  login: vi.fn(async () => ({ access_token: 'test-token', token_type: 'bearer' })),
  fetchMe: vi.fn(async () => {
    if (!mockUserStore.user) {
      const error = new Error('Not authenticated') as Error & {
        response: { status: number };
      };
      error.response = { status: 401 };
      throw error;
    }
    return mockUserStore.user;
  }),
}));

export function renderWithProviders(
  ui: ReactElement,
  { route = '/', user = ADMIN_USER }: { route?: string; user?: User | null } = {},
  options?: RenderOptions,
) {
  mockUserStore.user = user;
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 } },
  });
  if (user) {
    localStorage.setItem('ttg_access_token', 'test-token');
  } else {
    localStorage.removeItem('ttg_access_token');
  }
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <TooltipProvider>
          <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
        </TooltipProvider>
      </AuthProvider>
    </QueryClientProvider>,
    options,
  );
}
