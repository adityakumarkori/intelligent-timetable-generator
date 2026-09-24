import { useQuery } from '@tanstack/react-query';
import { EmptyState, ErrorState, LoadingState } from '@/components/common/States';
import { TimetableGrid } from '@/components/timetable/TimetableGrid';
import { parseApiError } from '@/services/api';
import { periodApi } from '@/services/masterApi';
import { timetableApi } from '@/services/timetableApi';
import { useMyFacultyId } from '@/pages/faculty/Dashboard';

export default function FacultyTimetablePage() {
  const profile = useMyFacultyId();
  const entries = useQuery({
    queryKey: ['faculty-timetable', profile.data?.id],
    queryFn: () =>
      timetableApi.facultyTimetable(profile.data!.id, { page: 1, page_size: 200 }),
    enabled: Boolean(profile.data?.id),
  });
  const periods = useQuery({
    queryKey: ['periods', 'grid'],
    queryFn: () => periodApi.list({ page: 1, page_size: 500 }),
  });

  if (profile.isPending) return <LoadingState label="Resolving faculty profile" />;
  if (profile.isError)
    return <ErrorState message={parseApiError(profile.error).message} onRetry={() => profile.refetch()} />;
  if (!profile.data) {
    return (
      <EmptyState
        title="No faculty profile linked"
        description="Your login is not linked to a faculty record, so a personal timetable cannot be resolved. Ask an administrator to link it, or browse published timetables."
      />
    );
  }

  return (
    <div className="grid gap-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">My timetable</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          {profile.data.name} ({profile.data.employee_code}) · classes across all visible timetables.
        </p>
      </div>
      {entries.isPending || periods.isPending ? (
        <LoadingState label="Loading timetable" />
      ) : entries.isError ? (
        <ErrorState message={parseApiError(entries.error).message} onRetry={() => entries.refetch()} />
      ) : periods.isError ? (
        <ErrorState message={parseApiError(periods.error).message} onRetry={() => periods.refetch()} />
      ) : entries.data.items.length === 0 ? (
        <EmptyState title="No classes scheduled" description="You have no entries in any visible timetable." />
      ) : (
        <>
          <p className="text-sm text-slate-500">
            {entries.data.total} scheduled class{entries.data.total === 1 ? '' : 'es'}
            {entries.data.total > entries.data.items.length &&
              ` (showing first ${entries.data.items.length})`}
            . Division shown per class.
          </p>
          <TimetableGrid periods={periods.data.items} entries={entries.data.items} />
        </>
      )}
    </div>
  );
}
