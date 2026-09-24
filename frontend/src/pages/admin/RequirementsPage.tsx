import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Pencil, Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { z } from 'zod';
import { ConfirmDialog } from '@/components/common/ConfirmDialog';
import { Field } from '@/components/common/Field';
import { Pagination } from '@/components/common/Pagination';
import { EmptyState, ErrorState, LoadingState } from '@/components/common/States';
import { OptionSelect } from '@/components/common/OptionSelect';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { parseApiError } from '@/services/api';
import { requirementApi } from '@/services/schedulingApi';
import type { ListParams } from '@/services/crud';
import type { DivisionSubjectRequirement } from '@/types/api';
import { ROOM_TYPES } from '@/types/api';

const schema = z.object({
  division_id: z.string().min(1, 'Division is required'),
  subject_id: z.string().min(1, 'Subject is required'),
  academic_session_id: z.string().min(1, 'Academic session is required'),
  required_periods_per_week: z
    .string()
    .refine(
      (v) => {
        const n = Number(v);
        return v.trim() !== '' && Number.isInteger(n) && n >= 1;
      },
      { message: 'Enter at least 1 period per week' },
    ),
  preferred_room_type: z.string().optional(),
  requires_lab: z.boolean(),
});

type FormValues = z.infer<typeof schema>;

export default function RequirementsPage() {
  const queryClient = useQueryClient();
  const [params, setParams] = useState<ListParams>({ page: 1, page_size: 20 });
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<DivisionSubjectRequirement | null>(null);

  const query = useQuery({
    queryKey: ['requirements', params],
    queryFn: () => requirementApi.list(params),
  });

  const { control, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['requirements'] });

  const save = useMutation({
    mutationFn: (values: FormValues) => {
      const body: Record<string, unknown> = {
        required_periods_per_week: Number(values.required_periods_per_week),
        requires_lab: values.requires_lab,
      };
      if (values.preferred_room_type) body.preferred_room_type = values.preferred_room_type;
      if (editing) return requirementApi.update(editing.id, body);
      return requirementApi.create({
        division_id: values.division_id,
        subject_id: values.subject_id,
        academic_session_id: values.academic_session_id,
        ...body,
      });
    },
    onSuccess: () => {
      toast.success(editing ? 'Requirement updated' : 'Requirement created');
      setOpen(false);
      invalidate();
    },
    onError: (error) => toast.error(parseApiError(error).message),
  });

  const remove = useMutation({
    mutationFn: (id: string) => requirementApi.remove(id),
    onSuccess: () => {
      toast.success('Requirement deleted');
      invalidate();
    },
    onError: (error) => toast.error(parseApiError(error).message),
  });

  function openCreate() {
    reset({
      division_id: (params.division_id as string) ?? '',
      subject_id: '',
      academic_session_id: (params.academic_session_id as string) ?? '',
      required_periods_per_week: '3',
      preferred_room_type: '',
      requires_lab: false,
    });
    setEditing(null);
    setOpen(true);
  }

  function openEdit(row: DivisionSubjectRequirement) {
    reset({
      division_id: row.division_id,
      subject_id: row.subject_id,
      academic_session_id: row.academic_session_id,
      required_periods_per_week: String(row.required_periods_per_week),
      preferred_room_type: row.preferred_room_type ?? '',
      requires_lab: row.requires_lab,
    });
    setEditing(row);
    setOpen(true);
  }

  const rows = query.data?.items ?? [];

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Weekly requirements</h1>
          <p className="mt-0.5 max-w-2xl text-sm text-slate-500">
            How many periods per week each division needs of each subject. These requirements
            are what the scheduling engine turns into a timetable.
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus /> New requirement
        </Button>
      </div>

      <Alert variant="info" title="How generation uses this">
        Each row becomes N schedulable sessions (e.g. “5/week” → 5 sessions). The engine then
        assigns each session a period, an eligible faculty member, and a compatible room.
      </Alert>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <OptionSelect
          label="Division"
          kind="divisions"
          value={params.division_id as string | undefined}
          allowAll
          onChange={(v) => setParams({ ...params, page: 1, division_id: v })}
        />
        <OptionSelect
          label="Subject"
          kind="subjects"
          value={params.subject_id as string | undefined}
          allowAll
          onChange={(v) => setParams({ ...params, page: 1, subject_id: v })}
        />
        <OptionSelect
          label="Session"
          kind="sessions"
          value={params.academic_session_id as string | undefined}
          allowAll
          onChange={(v) => setParams({ ...params, page: 1, academic_session_id: v })}
        />
      </div>

      {query.isPending && <LoadingState />}
      {query.isError && (
        <ErrorState message={parseApiError(query.error).message} onRetry={() => query.refetch()} />
      )}
      {query.isSuccess && rows.length === 0 && (
        <EmptyState
          title="No requirements found"
          description="Without requirements the generator has nothing to schedule."
        />
      )}
      {query.isSuccess && rows.length > 0 && (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Division</TableHead>
                <TableHead>Subject</TableHead>
                <TableHead>Sessions/week</TableHead>
                <TableHead>Room requirement</TableHead>
                <TableHead>State</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="font-medium">{r.division_code}</TableCell>
                  <TableCell>{r.subject_code}</TableCell>
                  <TableCell className="tabular-nums">{r.required_periods_per_week}</TableCell>
                  <TableCell>
                    {r.requires_lab ? (
                      <Badge variant="info">LAB required</Badge>
                    ) : (
                      (r.preferred_room_type ?? <span className="text-slate-400">Any</span>)
                    )}
                  </TableCell>
                  <TableCell>
                    {r.is_active ? (
                      <Badge variant="success">Active</Badge>
                    ) : (
                      <Badge variant="secondary">Inactive</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="icon" onClick={() => openEdit(r)} aria-label="Edit">
                        <Pencil />
                      </Button>
                      <ConfirmDialog
                        trigger={
                          <Button variant="ghost" size="icon" aria-label="Delete">
                            <Trash2 className="text-red-600" />
                          </Button>
                        }
                        title="Delete requirement?"
                        description={`${r.division_code} → ${r.subject_code}`}
                        confirmLabel="Delete"
                        destructive
                        onConfirm={() => remove.mutateAsync(r.id)}
                      />
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <Pagination
            page={query.data.page}
            pageSize={query.data.page_size}
            total={query.data.total}
            onPage={(page) => setParams({ ...params, page })}
          />
        </>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? 'Edit requirement' : 'New requirement'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit((v) => save.mutateAsync(v))} className="grid gap-4">
            {save.isError && (
              <p className="text-sm text-red-600">{parseApiError(save.error).message}</p>
            )}
            {!editing && (
              <>
                <Field control={control} name="division_id" label="Division" required error={errors.division_id?.message}>
                  {({ value, onChange }) => (
                    <OptionSelect label="" kind="divisions" value={(value as string) || undefined} onChange={(v) => onChange(v ?? '')} />
                  )}
                </Field>
                <Field control={control} name="subject_id" label="Subject" required error={errors.subject_id?.message}>
                  {({ value, onChange }) => (
                    <OptionSelect label="" kind="subjects" value={(value as string) || undefined} onChange={(v) => onChange(v ?? '')} />
                  )}
                </Field>
                <Field control={control} name="academic_session_id" label="Academic session" required error={errors.academic_session_id?.message}>
                  {({ value, onChange }) => (
                    <OptionSelect label="" kind="sessions" value={(value as string) || undefined} onChange={(v) => onChange(v ?? '')} />
                  )}
                </Field>
              </>
            )}
            <Field
              control={control}
              name="required_periods_per_week"
              label="Sessions per week"
              required
              error={errors.required_periods_per_week?.message}
            >
              {({ value, onChange }) => (
                <Input
                  type="number"
                  min={1}
                  value={(value as number | string) ?? ''}
                  onChange={(e) => onChange(e.target.value)}
                />
              )}
            </Field>
            <Field control={control} name="preferred_room_type" label="Preferred room type" hint="Empty = any room (subject default applies).">
              {({ value, onChange }) => (
                <Select value={(value as string) || 'any'} onValueChange={(v) => onChange(v === 'any' ? '' : v)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Any room" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="any">Any room</SelectItem>
                    {ROOM_TYPES.map((t) => (
                      <SelectItem key={t} value={t}>
                        {t}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </Field>
            <Field control={control} name="requires_lab" label="Requires lab">
              {({ value, onChange }) => (
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    className="size-4 rounded border-slate-300"
                    checked={Boolean(value)}
                    onChange={(e) => onChange(e.target.checked)}
                  />
                  Lab sessions only
                </label>
              )}
            </Field>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting || save.isPending}>
                {isSubmitting || save.isPending ? 'Saving…' : editing ? 'Save changes' : 'Create'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
