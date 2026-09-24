import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Cpu, Table2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ErrorState, LoadingState } from '@/components/common/States';
import { StatusBadge } from '@/components/common/StatusBadge';
import { parseApiError } from '@/services/api';
import {
  academicSessionApi,
  divisionApi,
  facultyApi,
  roomApi,
  subjectApi,
} from '@/services/masterApi';
import { timetableApi } from '@/services/timetableApi';

function useTotal(
  key: string[],
  fetcher: () => Promise<{ total: number }>,
  enabled = true,
) {
  return useQuery({ queryKey: key, queryFn: fetcher, enabled });
}

function StatCard({ label, value, loading }: { label: string; value: number | string; loading: boolean }) {
  return (
    <Card>
      <CardContent className="pt-5">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
        <p className="mt-1 text-3xl font-bold tabular-nums text-slate-900">
          {loading ? '…' : value}
        </p>
      </CardContent>
    </Card>
  );
}

export default function AdminDashboard() {
  const faculty = useTotal(['count', 'faculty'], () =>
    facultyApi.list({ page: 1, page_size: 1, is_active: true }).then((r) => ({ total: r.total })),
  );
  const subjects = useTotal(['count', 'subjects'], () =>
    subjectApi.list({ page: 1, page_size: 1, is_active: true }).then((r) => ({ total: r.total })),
  );
  const divisions = useTotal(['count', 'divisions'], () =>
    divisionApi.list({ page: 1, page_size: 1, is_active: true }).then((r) => ({ total: r.total })),
  );
  const rooms = useTotal(['count', 'rooms'], () =>
    roomApi.list({ page: 1, page_size: 1, is_active: true }).then((r) => ({ total: r.total })),
  );
  const sessions = useTotal(['count', 'sessions'], () =>
    academicSessionApi.list({ page: 1, page_size: 1, is_active: true }).then((r) => ({ total: r.total })),
  );
  const activeSession = useQuery({
    queryKey: ['active-session'],
    queryFn: () => academicSessionApi.list({ page: 1, page_size: 1, is_active: true }),
  });

  const draft = useTotal(['count', 'timetables', 'DRAFT'], () =>
    timetableApi.list({ page: 1, page_size: 1, status: 'DRAFT' }).then((r) => ({ total: r.total })),
  );
  const valid = useTotal(['count', 'timetables', 'VALID'], () =>
    timetableApi.list({ page: 1, page_size: 1, status: 'VALID' }).then((r) => ({ total: r.total })),
  );
  const published = useTotal(['count', 'timetables', 'PUBLISHED'], () =>
    timetableApi.list({ page: 1, page_size: 1, status: 'PUBLISHED' }).then((r) => ({ total: r.total })),
  );

  const recent = useQuery({
    queryKey: ['recent-timetables'],
    queryFn: () => timetableApi.list({ page: 1, page_size: 5 }),
  });

  const loading = [faculty, subjects, divisions, rooms, sessions, draft, valid, published].some(
    (q) => q.isPending,
  );

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Dashboard</h1>
          <p className="text-sm text-slate-500">
            Active session:{' '}
            {activeSession.isPending
              ? '…'
              : (activeSession.data?.items[0]?.name ?? 'none — create one to enable generation')}
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline">
            <Link to="/admin/requirements">Manage requirements</Link>
          </Button>
          <Button asChild>
            <Link to="/admin/generate">
              <Cpu /> Generate timetable
            </Link>
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="Active faculty" value={faculty.data?.total ?? 0} loading={faculty.isPending} />
        <StatCard label="Active subjects" value={subjects.data?.total ?? 0} loading={subjects.isPending} />
        <StatCard label="Active divisions" value={divisions.data?.total ?? 0} loading={divisions.isPending} />
        <StatCard label="Active rooms" value={rooms.data?.total ?? 0} loading={rooms.isPending} />
        <StatCard label="Draft timetables" value={draft.data?.total ?? 0} loading={draft.isPending} />
        <StatCard label="Valid timetables" value={valid.data?.total ?? 0} loading={valid.isPending} />
        <StatCard label="Published timetables" value={published.data?.total ?? 0} loading={published.isPending} />
        <StatCard label="Active sessions" value={sessions.data?.total ?? 0} loading={sessions.isPending} />
      </div>
      {loading && <span className="sr-only">Loading dashboard</span>}

      <Card>
        <CardHeader>
          <CardTitle>Recent timetables</CardTitle>
        </CardHeader>
        <CardContent>
          {recent.isPending && <LoadingState />}
          {recent.isError && (
            <ErrorState message={parseApiError(recent.error).message} onRetry={() => recent.refetch()} />
          )}
          {recent.isSuccess && recent.data.items.length === 0 && (
            <p className="text-sm text-slate-500">
              No timetables yet.{' '}
              <Link to="/admin/generate" className="underline">
                Generate the first one
              </Link>
              .
            </p>
          )}
          {recent.isSuccess && recent.data.items.length > 0 && (
            <ul className="divide-y divide-slate-100">
              {recent.data.items.map((t) => (
                <li key={t.id} className="flex flex-wrap items-center gap-2 py-2 text-sm">
                  <Link to={`/admin/timetables/${t.id}`} className="font-medium hover:underline">
                    {t.division_code} · v{t.version}
                  </Link>
                  <StatusBadge status={t.status} />
                  <span className="ml-auto text-xs text-slate-500">
                    {t.entry_count} entries · {t.session_name}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <div className="mt-3">
            <Button asChild variant="outline" size="sm">
              <Link to="/admin/timetables">
                <Table2 /> View all timetables
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
