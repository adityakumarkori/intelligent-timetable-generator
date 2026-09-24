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
import { subjectApi } from '@/services/masterApi';
import type { ListParams } from '@/services/crud';
import { ROOM_TYPES, SUBJECT_TYPES } from '@/types/api';

export default function SubjectsPage() {
  return (
    <CrudPage
      title="Subjects"
      description="Courses with weekly load and room requirements that drive generation."
      entityName="Subject"
      queryKey={['subjects']}
      list={(p) => subjectApi.list(p)}
      createItem={(b) => subjectApi.create(b)}
      updateItem={(id, b) => subjectApi.update(id, b)}
      removeItem={(id) => subjectApi.remove(id)}
      deleteDescription={(r) => `Delete subject "${r.code}"? Blocked while scheduling data references it.`}
      filters={(params: ListParams, setParams) => (
        <div className="flex flex-wrap gap-2">
          <Input
            placeholder="Search code or name…"
            className="max-w-xs"
            defaultValue={(params.q as string) ?? ''}
            onChange={(e) => setParams({ ...params, q: e.target.value || undefined })}
          />
          <Select
            value={(params.subject_type as string) ?? 'all'}
            onValueChange={(v) => setParams({ ...params, subject_type: v === 'all' ? undefined : v })}
          >
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All types</SelectItem>
              {SUBJECT_TYPES.map((t) => (
                <SelectItem key={t} value={t}>
                  {t}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}
      columns={[
        { key: 'code', header: 'Code', render: (r) => <span className="font-medium">{r.code}</span> },
        { key: 'name', header: 'Name', render: (r) => r.name },
        { key: 'subject_type', header: 'Type', render: (r) => <Badge variant="outline">{r.subject_type}</Badge> },
        {
          key: 'required_periods_per_week',
          header: '/week',
          render: (r) => <span className="tabular-nums">{r.required_periods_per_week}</span>,
        },
        {
          key: 'required_room_type',
          header: 'Room',
          render: (r) => (r.requires_lab ? <Badge variant="info">LAB required</Badge> : (r.required_room_type ?? <span className="text-slate-400">Any</span>)),
        },
        {
          key: 'is_active',
          header: 'State',
          render: (r) =>
            r.is_active ? <Badge variant="success">Active</Badge> : <Badge variant="secondary">Inactive</Badge>,
        },
      ]}
      fields={[
        { name: 'code', label: 'Code', type: 'text', required: true, placeholder: 'CS201' },
        { name: 'name', label: 'Name', type: 'text', required: true, placeholder: 'Data Structures' },
        {
          name: 'subject_type',
          label: 'Type',
          type: 'select',
          required: true,
          options: SUBJECT_TYPES.map((t) => ({ value: t, label: t })),
        },
        { name: 'required_periods_per_week', label: 'Periods per week', type: 'number', required: true, min: 1 },
        {
          name: 'required_room_type',
          label: 'Required room type',
          type: 'select',
          hint: 'Leave empty for “any room”. Labs should require LAB.',
          options: [{ value: '', label: 'Any room' }, ...ROOM_TYPES.map((t) => ({ value: t, label: t }))],
        },
        { name: 'requires_lab', label: 'Requires lab', type: 'checkbox', defaultValue: false },
        { name: 'is_active', label: 'Active', type: 'checkbox' },
      ]}
    />
  );
}
