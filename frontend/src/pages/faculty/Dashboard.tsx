import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/auth/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { facultyApi } from '@/services/masterApi';
import { timetableApi } from '@/services/timetableApi';

export function useMyFacultyId() {
  const { user } = useAuth();
  return useQuery({
    queryKey: ['my-faculty-profile', user?.id],
    queryFn: async () => {
      const page = await facultyApi.list({ page: 1, page_size: 100 });
      return page.items.find((f) => f.user_id === user?.id) ?? null;
    },
    enabled: user?.role === 'FACULTY',
  });
}

export default function FacultyDashboard() {
  const { user } = useAuth();
  const profile = useMyFacultyId();
  const myClasses = useQuery({
    queryKey: ['my-classes', profile.data?.id],
    queryFn: () => timetableApi.facultyTimetable(profile.data!.id, { page: 1, page_size: 1 }),
    enabled: Boolean(profile.data?.id),
  });
  const published = useQuery({
    queryKey: ['published-count'],
    queryFn: () => timetableApi.list({ page: 1, page_size: 1, status: 'PUBLISHED' }),
  });

  return (
    <div className="grid gap-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Welcome, {user?.name ?? 'faculty'}</h1>
        <p className="text-sm text-slate-500">Your teaching schedule at a glance.</p>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">My scheduled classes</p>
            <p className="mt-1 text-3xl font-bold tabular-nums">
              {myClasses.isPending ? '…' : (myClasses.data?.total ?? 0)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Published timetables</p>
            <p className="mt-1 text-3xl font-bold tabular-nums">
              {published.isPending ? '…' : (published.data?.total ?? 0)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Linked profile</p>
            <p className="mt-1 text-lg font-bold">
              {profile.isPending ? '…' : (profile.data ? `${profile.data.name} (${profile.data.employee_code})` : 'Not linked')}
            </p>
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Quick actions</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button asChild>
            <Link to="/faculty/timetable">View my timetable</Link>
          </Button>
          <Button asChild variant="outline">
            <Link to="/faculty/published">Browse published timetables</Link>
          </Button>
        </CardContent>
      </Card>
      {profile.isSuccess && !profile.data && (
        <p className="text-sm text-amber-700">
          Your login is not linked to a faculty record yet — ask an administrator to link it so
          “My timetable” can resolve automatically.
        </p>
      )}
    </div>
  );
}
