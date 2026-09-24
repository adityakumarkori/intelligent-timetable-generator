import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { CrudPage } from '@/components/common/CrudPage';
import { departmentApi, facultyApi } from '@/services/masterApi';
import type { ListParams } from '@/services/crud';
import { DepartmentFilter } from '@/pages/admin/DivisionsPage';

async function departmentOptions() {
  const page = await departmentApi.list({ page: 1, page_size: 200 });
  return page.items.map((d) => ({ value: d.id, label: `${d.code} — ${d.name}` }));
}

export default function FacultyPage() {
  return (
    <CrudPage
      title="Faculty"
      description="Teaching staff. Optionally link a login user; availability is managed separately."
      entityName="Faculty member"
      queryKey={['faculty']}
      list={(p) => facultyApi.list(p)}
      createItem={(b) => facultyApi.create(b)}
      updateItem={(id, b) => facultyApi.update(id, b)}
      removeItem={(id) => facultyApi.remove(id)}
      deleteDescription={(r) => `Delete "${r.name}" (${r.employee_code})? Blocked while scheduling data references them.`}
      filters={(params: ListParams, setParams) => (
        <div className="flex flex-wrap gap-2">
          <Input
            placeholder="Search code or name…"
            className="max-w-xs"
            defaultValue={(params.q as string) ?? ''}
            onChange={(e) => setParams({ ...params, q: e.target.value || undefined })}
          />
          <DepartmentFilter
            value={params.department_id as string | undefined}
            onChange={(department_id) => setParams({ ...params, department_id })}
          />
        </div>
      )}
      columns={[
        { key: 'name', header: 'Name', render: (r) => <span className="font-medium">{r.name}</span> },
        { key: 'employee_code', header: 'Employee code', render: (r) => r.employee_code },
        {
          key: 'is_active',
          header: 'State',
          render: (r) =>
            r.is_active ? <Badge variant="success">Active</Badge> : <Badge variant="secondary">Inactive</Badge>,
        },
      ]}
      fields={[
        { name: 'name', label: 'Name', type: 'text', required: true, placeholder: 'Dr. Sharma' },
        { name: 'employee_code', label: 'Employee code', type: 'text', required: true, placeholder: 'FAC-001' },
        { name: 'department_id', label: 'Department', type: 'select', required: true, loadOptions: departmentOptions },
        {
          name: 'user_id',
          label: 'Linked user ID',
          type: 'text',
          hint: 'Optional UUID of the login account. Leave empty for none.',
          placeholder: 'UUID (optional)',
        },
        { name: 'is_active', label: 'Active', type: 'checkbox' },
      ]}
    />
  );
}
