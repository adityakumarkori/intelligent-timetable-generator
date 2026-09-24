import { useQuery } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { CrudPage } from '@/components/common/CrudPage';
import { academicSessionApi } from '@/services/masterApi';
import type { ListParams } from '@/services/crud';

export default function SessionsPage() {
  return (
    <CrudPage
      title="Academic Sessions"
      description="Terms for which timetables are generated. Only active sessions are schedulable."
      entityName="Session"
      queryKey={['academic-sessions']}
      list={(p) => academicSessionApi.list(p)}
      createItem={(b) => academicSessionApi.create(b)}
      updateItem={(id, b) => academicSessionApi.update(id, b)}
      removeItem={(id) => academicSessionApi.remove(id)}
      deleteDescription={(r) => `Delete session "${r.name}"? Blocked while scheduling data references it.`}
      filters={(params: ListParams, setParams) => (
        <div className="flex flex-wrap gap-2">
          <Select
            value={params.is_active === undefined ? 'all' : String(params.is_active)}
            onValueChange={(v) =>
              setParams({ ...params, is_active: v === 'all' ? undefined : v === 'true' })
            }
          >
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Active state" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All states</SelectItem>
              <SelectItem value="true">Active</SelectItem>
              <SelectItem value="false">Inactive</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}
      columns={[
        { key: 'name', header: 'Name', render: (r) => <span className="font-medium">{r.name}</span> },
        { key: 'dates', header: 'Dates', render: (r) => `${r.start_date} → ${r.end_date}` },
        {
          key: 'is_active',
          header: 'State',
          render: (r) =>
            r.is_active ? <Badge variant="success">Active</Badge> : <Badge variant="secondary">Inactive</Badge>,
        },
      ]}
      fields={[
        { name: 'name', label: 'Name', type: 'text', required: true, placeholder: 'e.g. 2026-27' },
        { name: 'start_date', label: 'Start date', type: 'date', required: true },
        { name: 'end_date', label: 'End date', type: 'date', required: true },
        { name: 'is_active', label: 'Active', type: 'checkbox' },
      ]}
    />
  );
}

export function useActiveSessions() {
  return useQuery({
    queryKey: ['academic-sessions', 'active-options'],
    queryFn: () => academicSessionApi.list({ page: 1, page_size: 100, is_active: true }),
  });
}
