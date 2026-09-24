import { useQuery } from '@tanstack/react-query';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { academicSessionApi, departmentApi, divisionApi, facultyApi, subjectApi } from '@/services/masterApi';

export interface Option {
  value: string;
  label: string;
}

async function fetchOptions(kind: string): Promise<Option[]> {
  switch (kind) {
    case 'departments': {
      const p = await departmentApi.list({ page: 1, page_size: 200 });
      return p.items.map((d) => ({ value: d.id, label: `${d.code} — ${d.name}` }));
    }
    case 'divisions': {
      const p = await divisionApi.list({ page: 1, page_size: 200 });
      return p.items.map((d) => ({ value: d.id, label: `${d.code} — ${d.name}` }));
    }
    case 'subjects': {
      const p = await subjectApi.list({ page: 1, page_size: 200 });
      return p.items.map((s) => ({ value: s.id, label: `${s.code} — ${s.name}` }));
    }
    case 'faculty': {
      const p = await facultyApi.list({ page: 1, page_size: 200 });
      return p.items.map((f) => ({ value: f.id, label: `${f.name} (${f.employee_code})` }));
    }
    case 'sessions': {
      const p = await academicSessionApi.list({ page: 1, page_size: 100 });
      return p.items.map((s) => ({ value: s.id, label: s.name }));
    }
    default:
      return [];
  }
}

export function useOptions(kind: string) {
  return useQuery({ queryKey: ['options', kind], queryFn: () => fetchOptions(kind), staleTime: 60_000 });
}

export function OptionSelect({
  label,
  kind,
  value,
  onChange,
  placeholder,
  allowAll = false,
  allLabel = 'All',
}: {
  label: string;
  kind: string;
  value?: string;
  onChange: (value: string | undefined) => void;
  placeholder?: string;
  allowAll?: boolean;
  allLabel?: string;
}) {
  const { data, isPending } = useOptions(kind);
  return (
    <div className="grid gap-1.5">
      <Label>{label}</Label>
      <Select
        value={value ?? (allowAll ? 'all' : '')}
        onValueChange={(v) => onChange(allowAll && v === 'all' ? undefined : v)}
        disabled={isPending}
      >
        <SelectTrigger className="w-full min-w-44">
          <SelectValue placeholder={placeholder ?? (isPending ? 'Loading…' : `Select ${label.toLowerCase()}`)} />
        </SelectTrigger>
        <SelectContent>
          {allowAll && <SelectItem value="all">{allLabel}</SelectItem>}
          {(data ?? []).map((o) => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
