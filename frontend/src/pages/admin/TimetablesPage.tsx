import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Cpu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Pagination } from '@/components/common/Pagination';
import { EmptyState, ErrorState, LoadingState } from '@/components/common/States';
import { OptionSelect } from '@/components/common/OptionSelect';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { parseApiError } from '@/services/api';
import type { ListParams } from '@/services/crud';
import { timetableApi } from '@/services/timetableApi';
import { TIMETABLE_STATUSES } from '@/types/api';

export default function TimetablesPage() {
  const [params, setParams] = useState<ListParams>({ page: 1, page_size: 20 });
  const query = useQuery({
    queryKey: ['timetables', params],
    queryFn: () => timetableApi.list(params),
  });
  const rows = query.data?.items ?? [];

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Timetables</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Every generated version, with status. Filter by division + session to see version history.
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild>
            <Link to="/admin/generate">
              <Cpu /> Generate
            </Link>
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="grid gap-3 pt-5 sm:grid-cols-3">
          <OptionSelect
            label="Division"
            kind="divisions"
            value={params.division_id as string | undefined}
            allowAll
            onChange={(v) => setParams({ ...params, page: 1, division_id: v })}
          />
          <OptionSelect
            label="Session"
            kind="sessions"
            value={params.academic_session_id as string | undefined}
            allowAll
            onChange={(v) => setParams({ ...params, page: 1, academic_session_id: v })}
          />
          <div className="grid gap-1.5">
            <label className="text-sm font-medium text-slate-700">Status</label>
            <Select
              value={(params.status as string) ?? 'all'}
              onValueChange={(v) => setParams({ ...params, page: 1, status: v === 'all' ? undefined : v })}
            >
              <SelectTrigger>
                <SelectValue placeholder="All statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                {TIMETABLE_STATUSES.map((s) => (
                  <SelectItem key={s} value={s}>
                    {s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {query.isPending && <LoadingState />}
      {query.isError && (
        <ErrorState message={parseApiError(query.error).message} onRetry={() => query.refetch()} />
      )}
      {query.isSuccess && rows.length === 0 && (
        <EmptyState
          title="No timetables found"
          description="Generate one to get started."
          action={
            <Button asChild>
              <Link to="/admin/generate">
                <Cpu /> Generate timetable
              </Link>
            </Button>
          }
        />
      )}
      {query.isSuccess && rows.length > 0 && (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Division</TableHead>
                <TableHead>Version</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Entries</TableHead>
                <TableHead>Session</TableHead>
                <TableHead>Updated</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((t) => (
                <TableRow key={t.id}>
                  <TableCell>
                    <Link to={`/admin/timetables/${t.id}`} className="font-medium hover:underline">
                      {t.division_code}
                    </Link>
                  </TableCell>
                  <TableCell className="tabular-nums">v{t.version}</TableCell>
                  <TableCell>
                    <StatusBadge status={t.status} />
                  </TableCell>
                  <TableCell className="tabular-nums">{t.entry_count}</TableCell>
                  <TableCell>{t.session_name}</TableCell>
                  <TableCell className="text-xs text-slate-500">
                    {new Date(t.updated_at).toLocaleString()}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <Pagination
            page={query.data.page}
            pageSize={query.data.page_size}
            total={query.data.total}
            onPage={(page) => setParams({ ...params, page })}
          />
        </>
      )}
    </div>
  );
}
