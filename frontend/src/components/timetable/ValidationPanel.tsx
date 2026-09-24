import { AlertTriangle, CheckCircle2, Lightbulb, RefreshCw, XCircle } from 'lucide-react';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { ValidateResult } from '@/types/api';

export function ValidationPanel({
  result,
  isPending,
  error,
  onValidate,
  validating,
  compact = false,
}: {
  result?: ValidateResult | null;
  isPending?: boolean;
  error?: string | null;
  onValidate: () => void;
  validating?: boolean;
  compact?: boolean;
}) {
  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <Button size="sm" variant="outline" onClick={onValidate} disabled={validating}>
          <RefreshCw className={validating ? 'animate-spin' : ''} />
          {validating ? 'Validating…' : 'Validate timetable'}
        </Button>
        {isPending && <span className="text-sm text-slate-500">Checking…</span>}
        {result && (
          <span className="flex items-center gap-2 text-sm">
            {result.valid ? (
              <>
                <CheckCircle2 className="size-4 text-green-600" aria-hidden />
                <span className="font-semibold text-green-700">Valid</span>
              </>
            ) : (
              <>
                <XCircle className="size-4 text-red-600" aria-hidden />
                <span className="font-semibold text-red-700">Validation failed</span>
              </>
            )}
            {result.score !== null && result.score !== undefined && (
              <Badge variant="secondary">Score: {result.score}</Badge>
            )}
          </span>
        )}
      </div>

      {error && (
        <Alert variant="destructive" title="Validation failed to run">
          {error}
        </Alert>
      )}

      {result && !result.valid && (
        <div className="grid gap-2">
          {result.errors.length === 0 && result.violations.length === 0 && (
            <Alert variant="destructive" title="Invalid">
              The timetable failed validation without detailed errors.
            </Alert>
          )}
          {(result.errors.length > 0 ? result.errors : result.violations).map((v, i) => (
            <div key={i} className="rounded-lg border border-red-200 bg-white p-3">
              <div className="flex flex-wrap items-center gap-2">
                <XCircle className="size-4 text-red-600" aria-hidden />
                <Badge variant="destructive">{v.type}</Badge>
              </div>
              <p className="mt-1.5 text-sm text-slate-800">{v.message}</p>
            </div>
          ))}
        </div>
      )}

      {result?.valid && !compact && (
        <Alert variant="success" title="All hard constraints pass">
          This timetable satisfies every scheduling rule the validator checks.
        </Alert>
      )}

      {result && result.warnings.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
          <p className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-amber-800">
            <AlertTriangle className="size-3" aria-hidden />
            Quality warnings ({result.warnings.length}) — advisory only
          </p>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-amber-900">
            {result.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
          <p className="mt-2 flex items-center gap-1 text-xs text-amber-800">
            <Lightbulb className="size-3" aria-hidden />
            Warnings never block publishing; they describe soft-constraint quality.
          </p>
        </div>
      )}
    </div>
  );
}
