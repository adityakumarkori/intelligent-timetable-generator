import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/auth/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { timetableApi } from '@/services/timetableApi';

export default function StudentDashboard() {
  const { user } = useAuth();
  const published = useQuery({
    queryKey: ['published-count'],
    queryFn: () => timetableApi.list({ page: 1, page_size: 1, status: 'PUBLISHED' }),
  });
  const recent = useQuery({
    queryKey: ['published-recent'],
    queryFn: () => timetableApi.list({ page: 1, page_size: 5, status: 'PUBLISHED' }),
  });

  return (
    <div className="grid gap-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Welcome, {user?.name ?? 'student'}</h1>
        <p className="text-sm text-slate-500">Published class schedules.</p>
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <Card>
          <CardContent className="pt-5">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Published timetables
            </p>
            <p className="mt-1 text-3xl font-bold tabular-nums">
              {published.isPending ? '…' : (published.data?.total ?? 0)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Quick actions</CardTitle>
          </CardHeader>
          <CardContent>
            <Button asChild>
              <Link to="/student/timetable">View my timetable</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Recently published</CardTitle>
        </CardHeader>
        <CardContent>
          {recent.isSuccess && recent.data.items.length === 0 && (
            <p className="text-sm text-slate-500">No published timetables yet.</p>
          )}
          {recent.isSuccess && (
            <ul className="divide-y divide-slate-100">
              {recent.data.items.map((t) => (
                <li key={t.id} className="py-2 text-sm">
                  <Link to="/student/timetable" className="font-medium hover:underline">
                    {t.division_code} · v{t.version}
                  </Link>{' '}
                  <span className="text-slate-500">· {t.entry_count} entries · {t.session_name}</span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
