import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { z } from 'zod';
import { ConfirmDialog } from '@/components/common/ConfirmDialog';
import { Field } from '@/components/common/Field';
import { Pagination } from '@/components/common/Pagination';
import { EmptyState, ErrorState, LoadingState } from '@/components/common/States';
import { OptionSelect } from '@/components/common/OptionSelect';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { parseApiError } from '@/services/api';
import { assignmentApi } from '@/services/schedulingApi';
import type { ListParams } from '@/services/crud';

const schema = z.object({
  faculty_id: z.string().min(1, 'Faculty is required'),
  subject_id: z.string().min(1, 'Subject is required'),
  division_id: z.string().min(1, 'Division is required'),
  academic_session_id: z.string().min(1, 'Academic session is required'),
});

type FormValues = z.infer<typeof schema>;

export default function AssignmentsPage() {
  const queryClient = useQueryClient();
  const [params, setParams] = useState<ListParams>({ page: 1, page_size: 20 });
  const [open, setOpen] = useState(false);

  const query = useQuery({
    queryKey: ['assignments', params],
    queryFn: () => assignmentApi.list(params),
  });

  const { control, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['assignments'] });

  const create = useMutation({
    mutationFn: (values: FormValues) => assignmentApi.create(values as Record<string, unknown>),
    onSuccess: () => {
      toast.success('Assignment created');
      setOpen(false);
      invalidate();
    },
    onError: (error) => toast.error(parseApiError(error).message),
  });

  const remove = useMutation({
    mutationFn: (id: string) => assignmentApi.remove(id),
    onSuccess: () => {
      toast.success('Assignment deleted');
      invalidate();
    },
    onError: (error) => toast.error(parseApiError(error).message),
  });

  const existing = new Set(
    (query.data?.items ?? []).map((a) => `${a.faculty_id}|${a.subject_id}|${a.division_id}|${a.academic_session_id}`),
  );

  async function submit(values: FormValues) {
    const key = `${values.faculty_id}|${values.subject_id}|${values.division_id}|${values.academic_session_id}`;
    if (existing.has(key)) {
      toast.error('This exact assignment already exists in the list below.');
      return;
    }
    await create.mutateAsync(values);
  }

  const rows = query.data?.items ?? [];

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Faculty assignments</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Who may teach which subject to which division in which session. The generator only
            schedules valid assignments — never arbitrary pairs.
          </p>
        </div>
        <Button
          onClick={() => {
            reset({ faculty_id: '', subject_id: '', division_id: '', academic_session_id: '' });
            setOpen(true);
          }}
        >
          <Plus /> New assignment
        </Button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <OptionSelect
          label="Faculty"
          kind="faculty"
          value={params.faculty_id as string | undefined}
          allowAll
          onChange={(v) => setParams({ ...params, page: 1, faculty_id: v })}
        />
        <OptionSelect
          label="Subject"
          kind="subjects"
          value={params.subject_id as string | undefined}
          allowAll
          onChange={(v) => setParams({ ...params, page: 1, subject_id: v })}
        />
        <OptionSelect
          label="Division"
          kind="divisions"
          value={params.division_id as string | undefined}
          allowAll
          onChange={(v) => setParams({ ...params, page: 1, division_id: v })}
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
          title="No assignments found"
          description="Create the first faculty → subject → division → session assignment."
        />
      )}
      {query.isSuccess && rows.length > 0 && (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Faculty</TableHead>
                <TableHead>Subject</TableHead>
                <TableHead>Division</TableHead>
                <TableHead>State</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((a) => (
                <TableRow key={a.id}>
                  <TableCell className="font-medium">{a.faculty_name}</TableCell>
                  <TableCell>{a.subject_code}</TableCell>
                  <TableCell>{a.division_code}</TableCell>
                  <TableCell>
                    {a.is_active ? (
                      <Badge variant="success">Active</Badge>
                    ) : (
                      <Badge variant="secondary">Inactive</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <ConfirmDialog
                      trigger={
                        <Button variant="ghost" size="icon" aria-label="Delete assignment">
                          <Trash2 className="text-red-600" />
                        </Button>
                      }
                      title="Delete assignment?"
                      description={`${a.faculty_name} → ${a.subject_code} → ${a.division_code}`}
                      confirmLabel="Delete"
                      destructive
                      onConfirm={() => remove.mutateAsync(a.id)}
                    />
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
            <DialogTitle>New assignment</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit((v) => submit(v))} className="grid gap-4">
            {create.isError && (
              <p className="text-sm text-red-600">{parseApiError(create.error).message}</p>
            )}
            <Field control={control} name="faculty_id" label="Faculty" required error={errors.faculty_id?.message}>
              {({ value, onChange }) => (
                <OptionSelect
                  label=""
                  kind="faculty"
                  value={(value as string) || undefined}
                  placeholder="Select faculty"
                  onChange={(v) => onChange(v ?? '')}
                />
              )}
            </Field>
            <Field control={control} name="subject_id" label="Subject" required error={errors.subject_id?.message}>
              {({ value, onChange }) => (
                <OptionSelect
                  label=""
                  kind="subjects"
                  value={(value as string) || undefined}
                  placeholder="Select subject"
                  onChange={(v) => onChange(v ?? '')}
                />
              )}
            </Field>
            <Field control={control} name="division_id" label="Division" required error={errors.division_id?.message}>
              {({ value, onChange }) => (
                <OptionSelect
                  label=""
                  kind="divisions"
                  value={(value as string) || undefined}
                  placeholder="Select division"
                  onChange={(v) => onChange(v ?? '')}
                />
              )}
            </Field>
            <Field
              control={control}
              name="academic_session_id"
              label="Academic session"
              required
              error={errors.academic_session_id?.message}
            >
              {({ value, onChange }) => (
                <OptionSelect
                  label=""
                  kind="sessions"
                  value={(value as string) || undefined}
                  placeholder="Select session"
                  onChange={(v) => onChange(v ?? '')}
                />
              )}
            </Field>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting || create.isPending}>
                {isSubmitting || create.isPending ? 'Saving…' : 'Create'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
