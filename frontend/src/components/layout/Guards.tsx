import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '@/auth/AuthContext';
import { ForbiddenState, LoadingState } from '@/components/common/States';
import type { UserRole } from '@/types/api';

export function RequireAuth() {
  const { user, isLoading } = useAuth();
  const location = useLocation();
  if (isLoading) {
    return (
      <main className="mx-auto max-w-4xl p-8">
        <LoadingState label="Checking session" />
      </main>
    );
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}

export function RequireRoles({ roles, children }: { roles: UserRole[]; children?: React.ReactNode }) {
  const { user, hasRole } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (!hasRole(...roles)) return <ForbiddenState />;
  return <>{children ?? <Outlet />}</>;
}
