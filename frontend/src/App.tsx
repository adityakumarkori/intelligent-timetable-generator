import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import api from '@/services/api';
import { cn } from '@/lib/utils';

type HealthResponse = {
  status: string;
  service: string;
  version: string;
};

async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>('/health');
  return data;
}

export default function App() {
  const { data, isPending, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['backend-health'],
    queryFn: fetchHealth,
    retry: 1,
  });

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 p-8">
      <div>
        <h1 className="text-3xl font-semibold">Intelligent Timetable Generator</h1>
        <p className="mt-2 text-sm text-gray-600">
          Phase 1 foundation — React + FastAPI wiring check.
        </p>
      </div>

      <section className="rounded-lg border p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-medium">Backend health</h2>
          <span
            className={cn(
              'rounded-full px-3 py-1 text-xs font-medium',
              data?.status === 'ok' && 'bg-green-100 text-green-800',
              isError && 'bg-red-100 text-red-800',
              isPending && 'bg-gray-100 text-gray-600',
            )}
          >
            {isPending ? 'checking…' : isError ? 'unreachable' : data?.status}
          </span>
        </div>

        {isError && (
          <p className="mt-3 text-sm text-red-700">
            Cannot reach {api.defaults.baseURL}/health — start the backend first.{' '}
            {error instanceof Error ? error.message : ''}
          </p>
        )}
        {data && (
          <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
            <dt className="text-gray-500">Service</dt>
            <dd>{data.service}</dd>
            <dt className="text-gray-500">Version</dt>
            <dd>{data.version}</dd>
          </dl>
        )}

        <button
          type="button"
          onClick={() => refetch()}
          disabled={isFetching}
          className="mt-4 rounded-md border px-3 py-1.5 text-sm hover:bg-gray-50 disabled:opacity-50"
        >
          {isFetching ? 'Rechecking…' : 'Recheck'}
        </button>
      </section>

      <nav className="text-sm text-gray-600">
        <Link to="/dashboard" className="underline">
          Go to dashboard placeholder
        </Link>
      </nav>
    </main>
  );
}
