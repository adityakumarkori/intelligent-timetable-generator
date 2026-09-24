import '@/test-utils';
import { ADMIN_USER, mockUserStore, renderWithProviders } from '@/test-utils';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthProvider } from '@/auth/AuthContext';
import LoginPage from '@/pages/LoginPage';

describe('LoginPage', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('shows validation errors on empty submit', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />, { user: null });
    await user.click(screen.getByRole('button', { name: /sign in/i }));
    expect(await screen.findByText(/email is required/i)).toBeInTheDocument();
    expect(await screen.findByText(/password is required/i)).toBeInTheDocument();
  });

  it('shows server error on invalid credentials', async () => {
    const { login } = await import('@/services/authApi');
    vi.mocked(login).mockRejectedValueOnce({
      response: { status: 401, data: { detail: 'Invalid email or password' } },
      isAxiosError: true,
    });
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />, { user: null });
    await user.type(screen.getByPlaceholderText(/admin@college.edu/i), 'a@x.edu');
    await user.type(screen.getByPlaceholderText(/••••/i), 'wrong');
    await user.click(screen.getByRole('button', { name: /sign in/i }));
    expect(await screen.findByText(/sign-in failed/i)).toBeInTheDocument();
  });

  it('redirects an already-authenticated user to their role home', async () => {
    mockUserStore.user = ADMIN_USER;
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: 0 } },
    });
    localStorage.setItem('ttg_access_token', 'test-token');
    const router = createMemoryRouter(
      [
        { path: '/login', element: <LoginPage /> },
        { path: '/admin', element: <div>ADMIN HOME</div> },
      ],
      { initialEntries: ['/login'] },
    );
    const { render } = await import('@testing-library/react');
    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </QueryClientProvider>,
    );
    await waitFor(() => {
      expect(screen.getByText('ADMIN HOME')).toBeInTheDocument();
    });
  });
});
