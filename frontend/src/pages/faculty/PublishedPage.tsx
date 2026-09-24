import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { EmptyState, ErrorState, LoadingState } from '@/components/common/States';
import { StatusBadge } from '@/components/common/StatusBadge';
import { TimetableGrid } from '@/components/timetable/TimetableGrid';
import { parseApiError } from '@/services/api';
import { periodApi } from '@/services/masterApi';
import { timetableApi } from '@/services/timetableApi';

export default function PublishedPage() {
  const published = useQuery({
    queryKey: ['published-list'],
    queryFn: () => timetableApi.list({ page: 1, page_size: 50, status: 'PUBLISHED' }),
  });
  const periods = useQuery({
    queryKey: ['periods', 'grid'],
    queryFn: () => periodApi.list({ page: 1, page_size: 100 }),
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const detail = useQuery({
    queryKey: ['timetable', selectedId],
    queryFn: () => timetableApi.get(selectedId!),
    enabled: Boolean(selectedId),
  });

  return (
    <div className="grid gap-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Published timetables</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Live schedules. Pick one to view the full weekly grid.
        </p>
      </div>

      {published.isPending && <LoadingState />}
      {published.isError && (
        <ErrorState message={parseApiError(published.error).message} onRetry={() => published.refetch()} />
      )}
      {published.isSuccess && published.data.items.length === 0 && (
        <EmptyState title="Nothing published yet" description="Check back later." />
      )}
      {published.isSuccess && published.data.items.length > 0 && (
        <Card>
          <CardContent className="grid gap-2 pt-5">
            {published.data.items.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setSelectedId(t.id)}
                className={`flex flex-wrap items-center gap-2 rounded-md border px-3 py-2 text-left text-sm transition-colors ${
                  selectedId === t.id
                    ? 'border-slate-900 bg-slate-50'
                    : 'border-slate-200 hover:border-slate-400'
                }`}
              >
                <span className="font-medium">
                  {t.division_code} · v{t.version}
                </span>
                <StatusBadge status={t.status} />
                <span className="text-xs text-slate-500">
                  {t.entry_count} entries · {t.session_name}
                </span>
              </button>
            ))}
          </CardContent>
        </Card>
      )}

      {selectedId && detail.isPending && <LoadingState label="Loading timetable" />}
      {selectedId && detail.isError && (
        <ErrorState message={parseApiError(detail.error).message} onRetry={() => detail.refetch()} />
      )}
      {selectedId && detail.isSuccess && periods.isSuccess && (
        <>
          <p className="text-sm text-slate-500">
            Showing {detail.data.division_code} · v{detail.data.version}
          </p>
          <TimetableGrid periods={periods.data.items} entries={detail.data.entries} />
        </>
      )}
      {selectedId && detail.isSuccess && periods.isPending && <LoadingState />}
    </div>
  );
}

export function FacultyPublishedLink() {
  return (
    <Button asChild variant="outline" size="sm">
      <Link to="/faculty/published">Browse published</Link>
    </Button>
  );
}
