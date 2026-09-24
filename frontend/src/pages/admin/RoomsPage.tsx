import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { CrudPage } from '@/components/common/CrudPage';
import { roomApi } from '@/services/masterApi';
import type { ListParams } from '@/services/crud';
import { ROOM_TYPES } from '@/types/api';

export default function RoomsPage() {
  return (
    <CrudPage
      title="Rooms"
      description="Classrooms and laboratories. Capacity drives fit checks during generation."
      entityName="Room"
      queryKey={['rooms']}
      list={(p) => roomApi.list(p)}
      createItem={(b) => roomApi.create(b)}
      updateItem={(id, b) => roomApi.update(id, b)}
      removeItem={(id) => roomApi.remove(id)}
      deleteDescription={(r) => `Delete room "${r.name}"? Blocked while scheduling data references it.`}
      filters={(params: ListParams, setParams) => (
        <div className="flex flex-wrap gap-2">
          <Input
            placeholder="Search room name…"
            className="max-w-xs"
            defaultValue={(params.q as string) ?? ''}
            onChange={(e) => setParams({ ...params, q: e.target.value || undefined })}
          />
          <Select
            value={(params.room_type as string) ?? 'all'}
            onValueChange={(v) => setParams({ ...params, room_type: v === 'all' ? undefined : v })}
          >
            <SelectTrigger className="w-44">
              <SelectValue placeholder="Room type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All types</SelectItem>
              {ROOM_TYPES.map((t) => (
                <SelectItem key={t} value={t}>
                  {t}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}
      columns={[
        { key: 'name', header: 'Room', render: (r) => <span className="font-medium">{r.name}</span> },
        { key: 'room_type', header: 'Type', render: (r) => <Badge variant="outline">{r.room_type}</Badge> },
        { key: 'capacity', header: 'Capacity', render: (r) => <span className="tabular-nums">{r.capacity}</span> },
        { key: 'building', header: 'Building', render: (r) => r.building ?? <span className="text-slate-400">—</span> },
        {
          key: 'is_active',
          header: 'State',
          render: (r) =>
            r.is_active ? <Badge variant="success">Active</Badge> : <Badge variant="secondary">Inactive</Badge>,
        },
      ]}
      fields={[
        { name: 'name', label: 'Room name/number', type: 'text', required: true, placeholder: 'Room 204' },
        {
          name: 'room_type',
          label: 'Room type',
          type: 'select',
          required: true,
          options: ROOM_TYPES.map((t) => ({ value: t, label: t })),
        },
        { name: 'capacity', label: 'Capacity', type: 'number', required: true, min: 1 },
        { name: 'building', label: 'Building', type: 'text', placeholder: 'Main block (optional)' },
        { name: 'is_active', label: 'Active', type: 'checkbox' },
      ]}
    />
  );
}
