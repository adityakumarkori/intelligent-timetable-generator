import { Plus } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Tooltip } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { PeriodBrief, TimetableEntry } from '@/types/api';
import { DAYS_OF_WEEK } from '@/types/api';

interface Slot {
  key: string;
  label: string;
  order: number;
}

function slotOf(p: PeriodBrief): Slot {
  const trim = (t: string) => t.slice(0, 5);
  return {
    key: `${trim(p.start_time)}-${trim(p.end_time)}-${p.period_order}`,
    label: `${trim(p.start_time)} – ${trim(p.end_time)}`,
    order: p.period_order,
  };
}

export function TimetableGrid({
  periods,
  entries,
  editable = false,
  onAdd,
  onEdit,
  compact = false,
}: {
  periods: PeriodBrief[];
  entries: TimetableEntry[];
  editable?: boolean;
  onAdd?: (periodId: string) => void;
  onEdit?: (entry: TimetableEntry) => void;
  compact?: boolean;
}) {
  const days = DAYS_OF_WEEK.filter((d) => periods.some((p) => p.day_of_week === d));
  const slots = new Map<string, Slot>();
  const periodByDaySlot = new Map<string, PeriodBrief>();
  for (const p of periods) {
    const s = slotOf(p);
    if (!slots.has(s.key)) slots.set(s.key, s);
    periodByDaySlot.set(`${p.day_of_week}|${s.key}`, p);
  }
  const orderedSlots = [...slots.values()].sort((a, b) => a.order - b.order || a.key.localeCompare(b.key));
  const byPeriod = new Map(entries.map((e) => [e.period.id, e]));

  if (periods.length === 0) {
    return <p className="text-sm text-slate-500">No periods configured — the grid cannot be built.</p>;
  }

  return (
    <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
      <table className="w-full min-w-[720px] border-collapse text-sm">
        <thead>
          <tr className="bg-slate-50">
            <th className="sticky left-0 z-10 w-32 border-b border-r border-slate-200 bg-slate-50 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              Time
            </th>
            {days.map((d) => (
              <th
                key={d}
                className="border-b border-slate-200 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500"
              >
                {d.charAt(0) + d.slice(1).toLowerCase()}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {orderedSlots.map((slot) => (
            <tr key={slot.key} className="border-b border-slate-100 last:border-0">
              <td className="sticky left-0 z-10 border-r border-slate-200 bg-slate-50 px-3 py-2 align-top text-xs font-medium tabular-nums text-slate-600">
                {slot.label}
              </td>
              {days.map((day) => {
                const period = periodByDaySlot.get(`${day}|${slot.key}`);
                if (!period) {
                  return <td key={day} className="bg-slate-50/50 px-2 py-2" />;
                }
                const entry = byPeriod.get(period.id);
                if (!entry) {
                  return (
                    <td key={day} className="px-2 py-2 align-top">
                      {editable && !period.is_break ? (
                        <button
                          type="button"
                          onClick={() => onAdd?.(period.id)}
                          className="flex h-full min-h-14 w-full items-center justify-center rounded-md border border-dashed border-slate-300 text-slate-400 transition-colors hover:border-slate-500 hover:text-slate-600"
                          aria-label={`Add class on ${day} ${slot.label}`}
                        >
                          <Plus className="size-4" />
                        </button>
                      ) : (
                        <span className="block min-h-6 text-xs text-slate-300">—</span>
                      )}
                    </td>
                  );
                }
                const inner = (
                  <button
                    type="button"
                    disabled={!editable}
                    onClick={() => onEdit?.(entry)}
                    className={cn(
                      'block w-full rounded-md border border-slate-200 bg-white px-2 text-left shadow-sm transition-colors',
                      compact ? 'py-1' : 'py-1.5',
                      editable ? 'cursor-pointer hover:border-slate-900' : 'cursor-default',
                    )}
                  >
                    <span className="block truncate text-[13px] font-semibold text-slate-900">
                      {entry.subject_code} · {entry.subject_name}
                    </span>
                    <span className="block truncate text-xs text-slate-600">{entry.faculty_name}</span>
                    <span className="mt-0.5 block text-[11px] text-slate-500">
                      {entry.room_name}
                      {period.is_break ? ' · Break' : ''}
                    </span>
                  </button>
                );
                return (
                  <td key={day} className="px-2 py-2 align-top">
                    {editable ? (
                      inner
                    ) : (
                      <Tooltip content={`${entry.subject_name} · ${entry.faculty_name} · ${entry.room_name}`}>
                        {inner}
                      </Tooltip>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      {editable && (
        <p className="border-t border-slate-200 bg-slate-50 px-3 py-1.5 text-[11px] text-slate-500">
          Click a filled cell to edit · <Badge variant="outline">+</Badge> empty cell to add
        </p>
      )}
    </div>
  );
}
