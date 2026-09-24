import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { EmptyState, ErrorState, LoadingState } from '@/components/common/States';
import { OptionSelect } from '@/components/common/OptionSelect';
import { StatusBadge } from '@/components/common/StatusBadge';
import { TimetableGrid } from '@/components/timetable/TimetableGrid';
import { parseApiError } from '@/services/api';
import { periodApi } from '@/services/masterApi';
import { timetableApi } from '@/services/timetableApi';

export default function StudentTimetablePage() {
  const [divisionId, setDivisionId] = useState<string | undefined>(undefined);
  const detail = useQuery({
    queryKey: ['division-timetable', divisionId],
    queryFn: () => timetableApi.divisionTimetable(divisionId!),
    enabled: Boolean(divisionId),
    retry: false,
  });
  const periods = useQuery({
    queryKey: ['periods', 'grid'],
    queryFn: () => periodApi.list({ page: 1, page_size: 500 }),
  });

  return (
    <div className="grid gap-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">My timetable</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Select your division to see its published schedule.
        </p>
      </div>

      <div className="max-w-md">
        <OptionSelect label="Division" kind="divisions" value={divisionId} onChange={setDivisionId} />
      </div>

      {!divisionId && (
        <EmptyState
          title="Select a division"
          description="Only published timetables are visible to students."
        />
      )}

      {divisionId && detail.isPending && <LoadingState label="Loading timetable" />}
      {divisionId && detail.isError && parseApiError(detail.error).status === 404 && (
        <EmptyState
          title="No published timetable"
          description="This division has no published schedule yet. Check back later."
        />
      )}
      {divisionId && detail.isError && parseApiError(detail.error).status !== 404 && (
        <ErrorState
          message={parseApiError(detail.error).message}
          onRetry={() => detail.refetch()}
        />
      )}
      {divisionId && detail.isSuccess && (
        <>
          <p className="flex flex-wrap items-center gap-2 text-sm text-slate-600">
            <span className="font-medium text-slate-900">
              {detail.data.division_code} · v{detail.data.version}
            </span>
            <StatusBadge status={detail.data.status} />
            <span>
              {detail.data.entry_count} classes · {detail.data.session_name}
            </span>
          </p>
          {periods.isPending && <LoadingState />}
          {periods.isError && (
            <ErrorState message={parseApiError(periods.error).message} onRetry={() => periods.refetch()} />
          )}
          {periods.isSuccess && (
            <TimetableGrid periods={periods.data.items} entries={detail.data.entries} />
          )}
        </>
      )}
    </div>
  );
}
