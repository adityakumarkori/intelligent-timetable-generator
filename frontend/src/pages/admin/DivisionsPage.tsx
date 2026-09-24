import { useQuery } from '@tanstack/react-query';
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
import { departmentApi, divisionApi } from '@/services/masterApi';
import type { ListParams } from '@/services/crud';

async function departmentOptions() {
  const page = await departmentApi.list({ page: 1, page_size: 200 });
  return page.items.map((d) => ({ value: d.id, label: `${d.code} — ${d.name}` }));
}

export default function DivisionsPage() {
  return (
    <CrudPage
      title="Divisions"
      description="Classes within a department. Codes are unique per department."
      entityName="Division"
      queryKey={['divisions']}
      list={(p) => divisionApi.list(p)}
      createItem={(b) => divisionApi.create(b)}
      updateItem={(id, b) => divisionApi.update(id, b)}
      removeItem={(id) => divisionApi.remove(id)}
      deleteDescription={(r) => `Delete division "${r.code}"? Blocked while scheduling data references it.`}
      filters={(params: ListParams, setParams) => (
        <div className="flex flex-wrap gap-2">
          <Input
            placeholder="Search code or name…"
            className="max-w-xs"
            defaultValue={(params.q as string) ?? ''}
            onChange={(e) => setParams({ ...params, q: e.target.value || undefined })}
          />
        </div>
      )}
      columns={[
        { key: 'code', header: 'Code', render: (r) => <span className="font-medium">{r.code}</span> },
        { key: 'name', header: 'Name', render: (r) => r.name },
        { key: 'student_count', header: 'Students', render: (r) => <span className="tabular-nums">{r.student_count}</span> },
        {
          key: 'is_active',
          header: 'State',
          render: (r) =>
            r.is_active ? <Badge variant="success">Active</Badge> : <Badge variant="secondary">Inactive</Badge>,
        },
      ]}
      fields={[
        { name: 'department_id', label: 'Department', type: 'select', required: true, loadOptions: departmentOptions },
        { name: 'name', label: 'Name', type: 'text', required: true, placeholder: 'CSE-A' },
        { name: 'code', label: 'Code', type: 'text', required: true, placeholder: 'CSE-A' },
        { name: 'student_count', label: 'Student count', type: 'number', min: 0, hint: 'Drives room-capacity checks during generation.' },
        { name: 'is_active', label: 'Active', type: 'checkbox' },
      ]}
    />
  );
}

export function DepartmentFilter({
  value,
  onChange,
}: {
  value?: string;
  onChange: (departmentId: string | undefined) => void;
}) {
  return (
    <Select value={value ?? 'all'} onValueChange={(v) => onChange(v === 'all' ? undefined : v)}>
      <SelectTrigger className="w-52">
        <SelectValue placeholder="All departments" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">All departments</SelectItem>
        <DepartmentOptions />
      </SelectContent>
    </Select>
  );
}

function DepartmentOptions() {
  const { data } = useQuery({ queryKey: ['departments', 'options'], queryFn: departmentOptions });
  return (
    <>
      {(data ?? []).map((d) => (
        <SelectItem key={d.value} value={d.value}>
          {d.label}
        </SelectItem>
      ))}
    </>
  );
}
