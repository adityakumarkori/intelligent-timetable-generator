import { useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  BookOpen,
  Building2,
  CalendarDays,
  CalendarRange,
  ChevronRight,
  Clock,
  Cpu,
  DoorOpen,
  GraduationCap,
  LayoutDashboard,
  LogOut,
  Menu,
  Table2,
  Users,
  X,
} from 'lucide-react';
import { useAuth } from '@/auth/AuthContext';
import { clearToken } from '@/services/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';
import type { UserRole } from '@/types/api';

interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  end?: boolean;
}

const ADMIN_NAV: NavItem[] = [
  { to: '/admin', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/admin/academic-sessions', label: 'Academic Sessions', icon: CalendarRange },
  { to: '/admin/departments', label: 'Departments', icon: Building2 },
  { to: '/admin/divisions', label: 'Divisions', icon: GraduationCap },
  { to: '/admin/subjects', label: 'Subjects', icon: BookOpen },
  { to: '/admin/faculty', label: 'Faculty', icon: Users },
  { to: '/admin/rooms', label: 'Rooms', icon: DoorOpen },
  { to: '/admin/periods', label: 'Periods', icon: Clock },
  { to: '/admin/availability', label: 'Availability', icon: CalendarDays },
  { to: '/admin/assignments', label: 'Assignments', icon: Table2 },
  { to: '/admin/requirements', label: 'Requirements', icon: BookOpen },
  { to: '/admin/timetables', label: 'Timetables', icon: Table2 },
  { to: '/admin/generate', label: 'Generate', icon: Cpu },
];

const FACULTY_NAV: NavItem[] = [
  { to: '/faculty', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/faculty/timetable', label: 'My Timetable', icon: Table2 },
  { to: '/faculty/published', label: 'Published Timetables', icon: CalendarDays },
];

const STUDENT_NAV: NavItem[] = [
  { to: '/student', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/student/timetable', label: 'My Timetable', icon: Table2 },
];

function navFor(role: UserRole | undefined): NavItem[] {
  switch (role) {
    case 'ADMIN':
    case 'SUPER_ADMIN':
      return ADMIN_NAV;
    case 'FACULTY':
      return FACULTY_NAV;
    case 'STUDENT':
      return STUDENT_NAV;
    default:
      return [];
  }
}

const ROLE_BADGE: Record<UserRole, string> = {
  SUPER_ADMIN: 'bg-purple-100 text-purple-800',
  ADMIN: 'bg-blue-100 text-blue-800',
  FACULTY: 'bg-green-100 text-green-800',
  STUDENT: 'bg-amber-100 text-amber-800',
};

function Crumbs() {
  const { pathname } = useLocation();
  const parts = pathname.split('/').filter(Boolean);
  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-xs text-slate-500">
      {parts.map((part, i) => {
        const href = `/${parts.slice(0, i + 1).join('/')}`;
        const label = part.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
        const last = i === parts.length - 1;
        return (
          <span key={href} className="flex items-center gap-1">
            {i > 0 && <ChevronRight className="size-3" aria-hidden />}
            {last ? (
              <span className="font-medium text-slate-800">{label}</span>
            ) : (
              <Link to={href} className="hover:underline">
                {label}
              </Link>
            )}
          </span>
        );
      })}
    </nav>
  );
}

export function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const items = navFor(user?.role);

  function handleLogout() {
    logout();
    clearToken();
    navigate('/login', { replace: true });
  }

  const sidebar = (
    <div className="flex h-full flex-col">
      <nav className="flex-1 space-y-0.5 overflow-y-auto p-3" aria-label="Primary">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={() => setSidebarOpen(false)}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-slate-900 text-white'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
              )
            }
          >
            <item.icon className="size-4 shrink-0" aria-hidden />
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-slate-200 p-3 text-xs text-slate-500">
        <p className="font-medium text-slate-700">Timetable Engine</p>
        <p>CP-SAT · local solver</p>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen bg-slate-50">
      <aside className="hidden w-60 shrink-0 border-r border-slate-200 bg-white lg:block">
        <div className="sticky top-0 h-screen">{sidebar}</div>
      </aside>

      {sidebarOpen && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <div className="absolute inset-0 bg-slate-900/50" onClick={() => setSidebarOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-72 bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-200 p-3">
              <span className="font-semibold">Menu</span>
              <Button variant="ghost" size="icon" onClick={() => setSidebarOpen(false)} aria-label="Close menu">
                <X />
              </Button>
            </div>
            <div className="h-[calc(100%-57px)]">{sidebar}</div>
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 border-b border-slate-200 bg-white">
          <div className="flex items-center gap-2 px-4 py-2.5">
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open menu"
            >
              <Menu />
            </Button>
            <Link to="/" className="font-semibold text-slate-900">
              Timetable Generator
            </Link>
            <div className="ml-auto flex items-center gap-2">
              {user && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" className="max-w-56">
                      <span className="truncate">{user.name || user.email}</span>
                      <Badge className={cn('ml-1 shrink-0', ROLE_BADGE[user.role])}>{user.role}</Badge>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuLabel>
                      <div className="font-medium">{user.name || 'User'}</div>
                      <div className="font-normal text-slate-500">{user.email}</div>
                    </DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={handleLogout}>
                      <LogOut className="size-4" aria-hidden /> Log out
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>
          </div>
          <div className="border-t border-slate-100 px-4 py-1.5">
            <Crumbs />
          </div>
        </header>
        <main className="min-w-0 flex-1 p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
