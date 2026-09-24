import { AlertTriangle, Lightbulb, XCircle } from 'lucide-react';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';

function severityVariant(severity: string): 'destructive' | 'warning' | 'info' {
  const s = severity.toUpperCase();
  if (s.includes('ERROR') || s.includes('CRITICAL')) return 'destructive';
  if (s.includes('WARN')) return 'warning';
  return 'info';
}

export interface ConflictLike {
  type: string;
  message: string;
  severity?: string;
  subject?: string | null;
  division?: string | null;
  suggestions?: string[];
}

export function ConflictPanel({
  title = 'Unable to generate timetable',
  conflicts,
  suggestions,
}: {
  title?: string;
  conflicts: ConflictLike[];
  suggestions?: string[];
}) {
  const extra = (suggestions ?? []).filter(
    (s) => !conflicts.some((c) => c.suggestions?.includes(s)),
  );
  return (
    <div className="grid gap-3">
      <Alert variant="destructive" title={title}>
        {conflicts.length} blocking issue{conflicts.length === 1 ? '' : 's'} found. Nothing was
        scheduled — resolve the items below and try again.
      </Alert>
      {conflicts.map((c, i) => (
        <div key={i} className="rounded-lg border border-red-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-center gap-2">
            {(c.severity ?? 'ERROR') === 'ERROR' ? (
              <XCircle className="size-4 text-red-600" aria-hidden />
            ) : (
              <AlertTriangle className="size-4 text-amber-600" aria-hidden />
            )}
            <Badge variant={severityVariant(c.severity ?? 'ERROR')}>{c.type}</Badge>
            {c.subject && <Badge variant="outline">Subject: {c.subject}</Badge>}
            {c.division && <Badge variant="outline">Division: {c.division}</Badge>}
          </div>
          <p className="mt-2 text-sm font-medium text-slate-900">{c.message}</p>
          {(c.suggestions ?? []).length > 0 && (
            <div className="mt-2">
              <p className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <Lightbulb className="size-3" aria-hidden /> Suggestions
              </p>
              <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-slate-700">
                {(c.suggestions ?? []).map((s, j) => (
                  <li key={j}>{s}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ))}
      {extra.length > 0 && (
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <Lightbulb className="size-3" aria-hidden /> General suggestions
          </p>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-slate-700">
            {extra.map((s, j) => (
              <li key={j}>{s}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
