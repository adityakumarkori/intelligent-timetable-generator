import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { CrudPage } from '@/components/common/CrudPage';
import { departmentApi } from '@/services/masterApi';
import type { ListParams } from '@/services/crud';

export default function DepartmentsPage() {
  return (
    <CrudPage
      title="Departments"
      description="Top-level academic units. Codes must be unique."
      entityName="Department"
      queryKey={['departments']}
      list={(p) => departmentApi.list(p)}
      createItem={(b) => departmentApi.create(b)}
      updateItem={(id, b) => departmentApi.update(id, b)}
      removeItem={(id) => departmentApi.remove(id)}
      deleteDescription={(r) => `Delete department "${r.name}"? Blocked while divisions or faculty reference it.`}
      filters={(params: ListParams, setParams) => (
        <Input
          placeholder="Search code or name…"
          className="max-w-xs"
          defaultValue={(params.q as string) ?? ''}
          onChange={(e) => setParams({ ...params, q: e.target.value || undefined })}
        />
      )}
      columns={[
        { key: 'code', header: 'Code', render: (r) => <span className="font-medium">{r.code}</span> },
        { key: 'name', header: 'Name', render: (r) => r.name },
        {
          key: 'is_active',
          header: 'State',
          render: (r) =>
            r.is_active ? <Badge variant="success">Active</Badge> : <Badge variant="secondary">Inactive</Badge>,
        },
      ]}
      fields={[
        { name: 'name', label: 'Name', type: 'text', required: true, placeholder: 'Computer Science' },
        { name: 'code', label: 'Code', type: 'text', required: true, placeholder: 'CS' },
        { name: 'is_active', label: 'Active', type: 'checkbox' },
      ]}
    />
  );
}
