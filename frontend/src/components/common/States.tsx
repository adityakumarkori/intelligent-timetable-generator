import { Inbox, RefreshCw, TriangleAlert } from 'lucide-react';
import { Alert, type AlertProps } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { TableSkeleton } from '@/components/ui/skeleton';

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div aria-label={label}>
      <TableSkeleton />
    </div>
  );
}

export function EmptyState({
  title = 'Nothing here yet',
  description,
  action,
}: {
  title?: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
      <Inbox className="size-8 text-slate-400" aria-hidden />
      <p className="font-medium text-slate-800">{title}</p>
      {description && <p className="max-w-md text-sm text-slate-500">{description}</p>}
      {action}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <Alert variant="destructive" title="Something went wrong">
      <div className="flex flex-wrap items-center gap-3">
        <span className="flex-1">{message}</span>
        {onRetry && (
          <Button variant="outline" size="sm" onClick={onRetry}>
            <RefreshCw /> Retry
          </Button>
        )}
      </div>
    </Alert>
  );
}

export function ForbiddenState() {
  return (
    <Alert variant="warning" title="Permission denied">
      <p className="flex items-center gap-2">
        <TriangleAlert className="size-4" aria-hidden />
        Your role does not allow access to this page.
      </p>
    </Alert>
  );
}

export type { AlertProps };
