import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { EmptyState, ErrorState, LoadingState } from '@/components/common/States';
import { OptionSelect } from '@/components/common/OptionSelect';
import { parseApiError, periodLabel } from '@/services/api';
import { facultyApi, periodApi } from '@/services/masterApi';
import { availabilityApi } from '@/services/schedulingApi';
import { cn } from '@/lib/utils';
import type { Period } from '@/types/api';

const DAY_ORDER = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY'];

export default function AvailabilityPage() {
  const queryClient = useQueryClient();
  const [facultyId, setFacultyId] = useState<string | undefined>(undefined);
  const [unavailable, setUnavailable] = useState<Set<string>>(new Set());
  const [dirty, setDirty] = useState(false);

  const facultyList = useQuery({
    queryKey: ['faculty', 'options-full'],
    queryFn: () => facultyApi.list({ page: 1, page_size: 100 }),
  });

  const periods = useQuery({
    queryKey: ['periods', 'all'],
    queryFn: () => periodApi.list({ page: 1, page_size: 100 }),
  });

  const availability = useQuery({
    queryKey: ['availability', facultyId],
    queryFn: () => availabilityApi.list(facultyId!),
    enabled: Boolean(facultyId),
  });

  useEffect(() => {
    if (availability.data) {
      setUnavailable(
        new Set(availability.data.filter((a) => a.status === 'UNAVAILABLE').map((a) => a.period_id)),
      );
      setDirty(false);
    }
  }, [availability.data]);

  const byDay = useMemo(() => {
    const map = new Map<string, Period[]>();
    for (const p of periods.data?.items ?? []) {
      if (!map.has(p.day_of_week)) map.set(p.day_of_week, []);
      map.get(p.day_of_week)!.push(p);
    }
    for (const list of map.values()) list.sort((a, b) => a.period_order - b.period_order);
    return DAY_ORDER.filter((d) => map.has(d)).map((d) => ({ day: d, periods: map.get(d)! }));
  }, [periods.data]);

  const save = useMutation({
    mutationFn: () =>
      availabilityApi.replace(
        facultyId!,
        [...unavailable].map((period_id) => ({ period_id, status: 'UNAVAILABLE' as const })),
      ),
    onSuccess: () => {
      toast.success('Availability saved');
      setDirty(false);
      queryClient.invalidateQueries({ queryKey: ['availability', facultyId] });
    },
    onError: (error) => toast.error(parseApiError(error).message),
  });

  function toggle(periodId: string) {
    setUnavailable((prev) => {
      const next = new Set(prev);
      if (next.has(periodId)) next.delete(periodId);
      else next.add(periodId);
      return next;
    });
    setDirty(true);
  }

  return (
    <div className="grid gap-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Faculty availability</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Mark periods a faculty member <strong>cannot</strong> teach. Anything unmarked counts
          as <strong>available</strong> — missing rows mean AVAILABLE.
        </p>
      </div>

      <div className="max-w-md">
        <OptionSelect label="Faculty member" kind="faculty" value={facultyId} onChange={setFacultyId} />
      </div>

      {!facultyId && (
        <EmptyState title="Select a faculty member" description="Availability is managed per faculty member." />
      )}

      {facultyId && periods.isPending && <LoadingState />}
      {facultyId && periods.isError && (
        <ErrorState message={parseApiError(periods.error).message} onRetry={() => periods.refetch()} />
      )}
      {facultyId && availability.isError && (
        <ErrorState
          message={parseApiError(availability.error).message}
          onRetry={() => availability.refetch()}
        />
      )}

      {facultyId && periods.isSuccess && (
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <CardTitle>
                {facultyList.data?.items.find((f) => f.id === facultyId)?.name ?? 'Schedule'}
              </CardTitle>
              <div className="flex items-center gap-2">
                {dirty && <Badge variant="warning">Unsaved changes</Badge>}
                <Button size="sm" disabled={!dirty || save.isPending} onClick={() => save.mutate()}>
                  {save.isPending ? 'Saving…' : 'Save availability'}
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="grid gap-4">
            {byDay.length === 0 && (
              <p className="text-sm text-slate-500">No periods configured yet.</p>
            )}
            {byDay.map(({ day, periods: list }) => (
              <div key={day}>
                <p className="mb-2 text-sm font-semibold text-slate-700">
                  {day.charAt(0) + day.slice(1).toLowerCase()}
                </p>
                <div className="flex flex-wrap gap-2">
                  {list.map((p) => {
                    const blocked = unavailable.has(p.id);
                    return (
                      <button
                        key={p.id}
                        type="button"
                        disabled={p.is_break || !p.is_active}
                        title={
                          p.is_break
                            ? 'Break period — never scheduled'
                            : !p.is_active
                              ? 'Inactive period'
                              : blocked
                                ? 'Unavailable — click to mark available'
                                : 'Available — click to mark unavailable'
                        }
                        onClick={() => toggle(p.id)}
                        className={cn(
                          'rounded-md border px-3 py-2 text-left text-xs transition-colors',
                          p.is_break || !p.is_active
                            ? 'cursor-not-allowed border-slate-200 bg-slate-50 text-slate-400 line-through'
                            : blocked
                              ? 'border-red-300 bg-red-50 text-red-800 hover:bg-red-100'
                              : 'border-green-300 bg-green-50 text-green-800 hover:bg-green-100',
                        )}
                      >
                        <span className="block font-semibold">{periodLabel(p).split('·')[1]?.trim()}</span>
                        <span className="block text-[11px] opacity-80">
                          {p.is_break ? 'Break' : blocked ? 'Unavailable' : `P${p.period_order} · Available`}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
            {unavailable.size > 0 && (
              <Alert variant="info" title={`${unavailable.size} blocked period(s)`}>
                Only these periods are stored as UNAVAILABLE. Everything else is treated as available.
              </Alert>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
