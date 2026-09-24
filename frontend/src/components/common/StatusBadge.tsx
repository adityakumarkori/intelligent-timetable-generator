import { Badge } from '@/components/ui/badge';
import type { TimetableStatus } from '@/types/api';

const STATUS_VARIANT: Record<TimetableStatus, 'default' | 'secondary' | 'success' | 'warning' | 'destructive' | 'info'> = {
  DRAFT: 'secondary',
  GENERATED: 'info',
  VALID: 'success',
  PUBLISHED: 'default',
  ARCHIVED: 'warning',
};

const STATUS_HELP: Record<TimetableStatus, string> = {
  DRAFT: 'Changes are being made; the timetable must pass validation before publishing.',
  GENERATED: 'Produced by the scheduling engine; validate before publishing.',
  VALID: 'All hard constraints currently pass.',
  PUBLISHED: 'This timetable is live and immutable. Clone it to make changes.',
  ARCHIVED: 'Retired history; kept for reference only.',
};

export function StatusBadge({ status, showHelp = false }: { status: TimetableStatus; showHelp?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2">
      <Badge variant={STATUS_VARIANT[status]}>{status}</Badge>
      {showHelp && <span className="text-xs text-slate-500">{STATUS_HELP[status]}</span>}
    </span>
  );
}
