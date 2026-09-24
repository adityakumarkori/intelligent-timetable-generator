import { Navigate, createBrowserRouter } from 'react-router-dom';
import { roleHome, useAuth } from '@/auth/AuthContext';
import { AppShell } from '@/components/layout/AppShell';
import { RequireAuth, RequireRoles } from '@/components/layout/Guards';
import LoginPage from '@/pages/LoginPage';
import HealthPage from '@/pages/HealthPage';
import NotFoundPage from '@/pages/NotFoundPage';
import AdminDashboard from '@/pages/admin/Dashboard';
import SessionsPage from '@/pages/admin/SessionsPage';
import DepartmentsPage from '@/pages/admin/DepartmentsPage';
import DivisionsPage from '@/pages/admin/DivisionsPage';
import SubjectsPage from '@/pages/admin/SubjectsPage';
import FacultyPage from '@/pages/admin/FacultyPage';
import RoomsPage from '@/pages/admin/RoomsPage';
import PeriodsPage from '@/pages/admin/PeriodsPage';
import AvailabilityPage from '@/pages/admin/AvailabilityPage';
import AssignmentsPage from '@/pages/admin/AssignmentsPage';
import RequirementsPage from '@/pages/admin/RequirementsPage';
import TimetablesPage from '@/pages/admin/TimetablesPage';
import TimetableDetailPage from '@/pages/admin/TimetableDetailPage';
import GeneratePage from '@/pages/admin/GeneratePage';
import FacultyDashboard from '@/pages/faculty/Dashboard';
import FacultyTimetablePage from '@/pages/faculty/FacultyTimetablePage';
import PublishedPage from '@/pages/faculty/PublishedPage';
import StudentDashboard from '@/pages/student/Dashboard';
import StudentTimetablePage from '@/pages/student/StudentTimetablePage';

const ADMIN = ['ADMIN', 'SUPER_ADMIN'] as const;

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  { path: '/health', element: <HealthPage /> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: '/', element: <RoleIndex /> },
          {
            path: '/admin',
            element: (
              <RequireRoles roles={[...ADMIN]}>
                <AdminDashboard />
              </RequireRoles>
            ),
          },
          {
            path: '/admin/academic-sessions',
            element: (
              <RequireRoles roles={[...ADMIN]}>
                <SessionsPage />
              </RequireRoles>
            ),
          },
          {
            path: '/admin/departments',
            element: (
              <RequireRoles roles={[...ADMIN]}>
                <DepartmentsPage />
              </RequireRoles>
            ),
          },
          {
            path: '/admin/divisions',
            element: (
              <RequireRoles roles={[...ADMIN]}>
                <DivisionsPage />
              </RequireRoles>
            ),
          },
          {
            path: '/admin/subjects',
            element: (
              <RequireRoles roles={[...ADMIN]}>
                <SubjectsPage />
              </RequireRoles>
            ),
          },
          {
            path: '/admin/faculty',
            element: (
              <RequireRoles roles={[...ADMIN]}>
                <FacultyPage />
              </RequireRoles>
            ),
          },
          {
            path: '/admin/rooms',
            element: (
              <RequireRoles roles={[...ADMIN]}>
                <RoomsPage />
              </RequireRoles>
            ),
          },
          {
            path: '/admin/periods',
            element: (
              <RequireRoles roles={[...ADMIN]}>
                <PeriodsPage />
              </RequireRoles>
            ),
          },
          {
            path: '/admin/availability',
            element: (
              <RequireRoles roles={[...ADMIN]}>
                <AvailabilityPage />
              </RequireRoles>
            ),
          },
          {
            path: '/admin/assignments',
            element: (
              <RequireRoles roles={[...ADMIN]}>
                <AssignmentsPage />
              </RequireRoles>
            ),
          },
          {
            path: '/admin/requirements',
            element: (
              <RequireRoles roles={[...ADMIN]}>
                <RequirementsPage />
              </RequireRoles>
            ),
          },
          {
            path: '/admin/timetables',
            element: (
              <RequireRoles roles={[...ADMIN]}>
                <TimetablesPage />
              </RequireRoles>
            ),
          },
          {
            path: '/admin/timetables/:id',
            element: (
              <RequireRoles roles={[...ADMIN]}>
                <TimetableDetailPage />
              </RequireRoles>
            ),
          },
          {
            path: '/admin/timetables/:id/edit',
            element: (
              <RequireRoles roles={[...ADMIN]}>
                <TimetableDetailPage editMode />
              </RequireRoles>
            ),
          },
          {
            path: '/admin/timetables/:id/versions',
            element: (
              <RequireRoles roles={[...ADMIN]}>
                <TimetableDetailPage versionsMode />
              </RequireRoles>
            ),
          },
          {
            path: '/admin/generate',
            element: (
              <RequireRoles roles={[...ADMIN]}>
                <GeneratePage />
              </RequireRoles>
            ),
          },
          {
            path: '/faculty',
            element: (
              <RequireRoles roles={['FACULTY']}>
                <FacultyDashboard />
              </RequireRoles>
            ),
          },
          {
            path: '/faculty/timetable',
            element: (
              <RequireRoles roles={['FACULTY']}>
                <FacultyTimetablePage />
              </RequireRoles>
            ),
          },
          {
            path: '/faculty/published',
            element: (
              <RequireRoles roles={['FACULTY']}>
                <PublishedPage />
              </RequireRoles>
            ),
          },
          {
            path: '/student',
            element: (
              <RequireRoles roles={['STUDENT']}>
                <StudentDashboard />
              </RequireRoles>
            ),
          },
          {
            path: '/student/timetable',
            element: (
              <RequireRoles roles={['STUDENT']}>
                <StudentTimetablePage />
              </RequireRoles>
            ),
          },
        ],
      },
    ],
  },
  { path: '*', element: <NotFoundPage /> },
]);

function RoleIndex() {
  const { user, isLoading } = useAuth();
  if (isLoading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={roleHome(user.role)} replace />;
}
