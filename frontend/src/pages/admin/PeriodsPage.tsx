import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { CrudPage } from '@/components/common/CrudPage';
import { periodApi } from '@/services/masterApi';
import type { ListParams } from '@/services/crud';
import { DAYS_OF_WEEK } from '@/types/api';
import { periodLabel } from '@/services/api';

export default function PeriodsPage() {
  return (
    <CrudPage
      title="Periods"
      description="Scheduling slots. Break periods are never assigned to timetable entries."
      entityName="Period"
      queryKey={['periods']}
      list={(p) => periodApi.list(p)}
      createItem={(b) => periodApi.create(b)}
      updateItem={(id, b) => periodApi.update(id, b)}
      removeItem={(id) => periodApi.remove(id)}
      deleteDescription={() => 'Delete this period? Blocked while scheduling data references it.'}
      filters={(params: ListParams, setParams) => (
        <div className="flex flex-wrap gap-2">
          <Select
            value={(params.day_of_week as string) ?? 'all'}
            onValueChange={(v) => setParams({ ...params, day_of_week: v === 'all' ? undefined : v })}
          >
            <SelectTrigger className="w-44">
              <SelectValue placeholder="Day" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All days</SelectItem>
              {DAYS_OF_WEEK.map((d) => (
                <SelectItem key={d} value={d}>
                  {d.charAt(0) + d.slice(1).toLowerCase()}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={params.is_break === undefined ? 'all' : String(params.is_break)}
            onValueChange={(v) => setParams({ ...params, is_break: v === 'all' ? undefined : v === 'true' })}
          >
            <SelectTrigger className="w-44">
              <SelectValue placeholder="Kind" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Classes + breaks</SelectItem>
              <SelectItem value="false">Teaching only</SelectItem>
              <SelectItem value="true">Breaks only</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}
      columns={[
        {
          key: 'slot',
          header: 'Slot',
          render: (r) => <span className="font-medium">{periodLabel(r)}</span>,
        },
        {
          key: 'is_break',
          header: 'Kind',
          render: (r) =>
            r.is_break ? <Badge variant="warning">Break</Badge> : <Badge variant="secondary">Teaching</Badge>,
        },
        {
          key: 'is_active',
          header: 'State',
          render: (r) =>
            r.is_active ? <Badge variant="success">Active</Badge> : <Badge variant="secondary">Inactive</Badge>,
        },
      ]}
      fields={[
        {
          name: 'day_of_week',
          label: 'Day',
          type: 'select',
          required: true,
          options: DAYS_OF_WEEK.map((d) => ({
            value: d,
            label: d.charAt(0) + d.slice(1).toLowerCase(),
          })),
        },
        { name: 'start_time', label: 'Start time', type: 'time', required: true },
        { name: 'end_time', label: 'End time', type: 'time', required: true },
        { name: 'period_order', label: 'Order in day', type: 'number', required: true, min: 1 },
        { name: 'is_break', label: 'Break period', type: 'checkbox', defaultValue: false, hint: 'Breaks are never scheduled.' },
        { name: 'is_active', label: 'Active', type: 'checkbox' },
      ]}
    />
  );
}
