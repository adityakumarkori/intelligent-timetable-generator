import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Archive, Copy, Megaphone, Pencil, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { z } from 'zod';
import { ConfirmDialog } from '@/components/common/ConfirmDialog';
import { Field } from '@/components/common/Field';
import { EmptyState, ErrorState, LoadingState } from '@/components/common/States';
import { OptionSelect } from '@/components/common/OptionSelect';
import { StatusBadge } from '@/components/common/StatusBadge';
import { ConflictPanel } from '@/components/timetable/ConflictPanel';
import { TimetableGrid } from '@/components/timetable/TimetableGrid';
import { ValidationPanel } from '@/components/timetable/ValidationPanel';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { parseApiError, periodLabel } from '@/services/api';
import { periodApi, roomApi } from '@/services/masterApi';
import { timetableApi } from '@/services/timetableApi';
import type { TimetableEntry, ValidateResult } from '@/types/api';

const EDITABLE = ['DRAFT', 'GENERATED', 'VALID'] as const;

const entrySchema = z.object({
  subject_id: z.string().min(1, 'Subject is required'),
  faculty_id: z.string().min(1, 'Faculty is required'),
  room_id: z.string().min(1, 'Room is required'),
  period_id: z.string().min(1, 'Period is required'),
});

type EntryValues = z.infer<typeof entrySchema>;

function toHttpDate(iso: string): string {
  return new Date(iso).toUTCString();
}

function RoomSelect({
  value,
  onChange,
}: {
  value?: string;
  onChange: (v: string | undefined) => void;
}) {
  const rooms = useQuery({
    queryKey: ['rooms', 'options'],
    queryFn: () => roomApi.list({ page: 1, page_size: 100 }),
    staleTime: 60_000,
  });
  return (
    <Select value={value ?? ''} onValueChange={(v) => onChange(v)} disabled={rooms.isPending}>
      <SelectTrigger>
        <SelectValue placeholder={rooms.isPending ? 'Loading…' : 'Select room'} />
      </SelectTrigger>
      <SelectContent>
        {(rooms.data?.items ?? []).map((r) => (
          <SelectItem key={r.id} value={r.id}>
            {r.name} · {r.room_type} · cap {r.capacity}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

function PeriodSelect({
  value,
  onChange,
  locked,
}: {
  value?: string;
  onChange: (v: string | undefined) => void;
  locked: boolean;
}) {
  const periods = useQuery({
    queryKey: ['periods', 'teaching-options'],
    queryFn: () => periodApi.list({ page: 1, page_size: 100, is_break: false, is_active: true }),
    staleTime: 60_000,
  });
  return (
    <Select
      value={value ?? ''}
      onValueChange={locked ? () => undefined : (v) => onChange(v)}
      disabled={periods.isPending || locked}
    >
      <SelectTrigger>
        <SelectValue placeholder={periods.isPending ? 'Loading…' : 'Select period'} />
      </SelectTrigger>
      <SelectContent>
        {(periods.data?.items ?? []).map((p) => (
          <SelectItem key={p.id} value={p.id}>
            {periodLabel(p)}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export default function TimetableDetailPage({
  editMode = false,
  versionsMode = false,
}: {
  editMode?: boolean;
  versionsMode?: boolean;
}) {
  const { id = '' } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<TimetableEntry | null>(null);
  const [addPeriod, setAddPeriod] = useState<string | null>(null);
  const [entryError, setEntryError] = useState<string | null>(null);
  const [lastConflicts, setLastConflicts] = useState<
    { conflicts: ValidateResult['violations']; title: string } | null
  >(null);

  const detail = useQuery({
    queryKey: ['timetable', id],
    queryFn: () => timetableApi.get(id),
  });
  const periods = useQuery({
    queryKey: ['periods', 'grid'],
    queryFn: () => periodApi.list({ page: 1, page_size: 100 }),
  });
  const validation = useQuery({
    queryKey: ['timetable-validation', id],
    queryFn: () => timetableApi.generationResult(id),
    enabled: false,
  });

  const t = detail.data;
  const editable = Boolean(t && (EDITABLE as readonly string[]).includes(t.status));
  const stamp = t ? toHttpDate(t.updated_at) : null;

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['timetable', id] });
    queryClient.invalidateQueries({ queryKey: ['timetables'] });
    queryClient.invalidateQueries({ queryKey: ['timetable-validation', id] });
  };

  function staleHandler(error: unknown): boolean {
    const info = parseApiError(error);
    if (info.code === 'STALE_TIMETABLE') {
      toast.error(info.message, { description: 'Reloaded the latest version.' });
      refresh();
      return true;
    }
    return false;
  }

  const validate = useMutation({
    mutationFn: () => timetableApi.validate(id),
    onSuccess: (res) => {
      toast[res.valid ? 'success' : 'error'](
        res.valid ? 'Timetable is valid' : 'Timetable is invalid — see violations',
      );
      validation.refetch();
      refresh();
    },
    onError: (error) => toast.error(parseApiError(error).message),
  });

  const publish = useMutation({
    mutationFn: () => timetableApi.publish(id, stamp),
    onSuccess: (res) => {
      toast.success(`Version ${res.version} published`);
      refresh();
    },
    onError: (error) => {
      if (!staleHandler(error)) toast.error(parseApiError(error).message);
    },
  });

  const archive = useMutation({
    mutationFn: () => timetableApi.archive(id),
    onSuccess: () => {
      toast.success('Timetable archived');
      refresh();
    },
    onError: (error) => toast.error(parseApiError(error).message),
  });

  const clone = useMutation({
    mutationFn: () => timetableApi.clone(id),
    onSuccess: (res) => {
      toast.success(`Cloned as v${res.version} draft`);
      navigate(`/admin/timetables/${res.id}/edit`);
    },
    onError: (error) => toast.error(parseApiError(error).message),
  });

  const saveEntry = useMutation({
    mutationFn: (values: EntryValues) => {
      if (editing) return timetableApi.updateEntry(id, editing.id, values, stamp);
      if (!addPeriod) throw new Error('No period selected');
      return timetableApi.createEntry(id, { ...values, period_id: addPeriod }, stamp);
    },
    onSuccess: () => {
      toast.success(editing ? 'Entry updated' : 'Entry added');
      setEditing(null);
      setAddPeriod(null);
      setEntryError(null);
      refresh();
    },
    onError: (error) => {
      if (staleHandler(error)) {
        setEditing(null);
        setAddPeriod(null);
        return;
      }
      const info = parseApiError(error);
      setEntryError(info.message);
      if (info.conflicts.length > 0) {
        setLastConflicts({ conflicts: info.conflicts, title: 'Change rejected' });
      }
    },
  });

  const removeEntry = useMutation({
    mutationFn: (entryId: string) => timetableApi.deleteEntry(id, entryId),
    onSuccess: () => {
      toast.success('Entry deleted — timetable revalidated');
      refresh();
    },
    onError: (error) => {
      if (!staleHandler(error)) toast.error(parseApiError(error).message);
    },
  });

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<EntryValues>({ resolver: zodResolver(entrySchema) });

  function openAdd(periodId: string) {
    reset({ subject_id: '', faculty_id: '', room_id: '', period_id: periodId });
    setEditing(null);
    setAddPeriod(periodId);
    setEntryError(null);
  }

  function openEdit(entry: TimetableEntry) {
    reset({
      subject_id: entry.subject_id,
      faculty_id: entry.faculty_id,
      room_id: entry.room_id,
      period_id: entry.period.id,
    });
    setEditing(entry);
    setAddPeriod(null);
    setEntryError(null);
  }

  const versions = useQuery({
    queryKey: ['timetable-versions', t?.division_id, t?.academic_session_id],
    queryFn: () =>
      timetableApi.list({
        page: 1,
        page_size: 50,
        division_id: t!.division_id,
        academic_session_id: t!.academic_session_id,
      }),
    enabled: Boolean(versionsMode && t),
  });

  if (detail.isPending) return <LoadingState label="Loading timetable" />;
  if (detail.isError)
    return <ErrorState message={parseApiError(detail.error).message} onRetry={() => detail.refetch()} />;
  if (!t) return <EmptyState title="Timetable not found" />;

  const report: ValidateResult | null = validation.data
    ? {
        timetable_id: validation.data.timetable_id,
        valid: validation.data.valid,
        violations: validation.data.violations,
        status: validation.data.valid ? 'VALID' : 'INVALID',
        errors: validation.data.violations,
        warnings: [],
        score: null,
      }
    : null;

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="flex flex-wrap items-center gap-2 text-xl font-semibold text-slate-900">
            {t.division_code} · v{t.version} <StatusBadge status={t.status} showHelp />
          </h1>
          <p className="mt-0.5 text-sm text-slate-500">
            {t.session_name} · {t.entry_count} entries · updated{' '}
            {new Date(t.updated_at).toLocaleString()}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {editable && (
            <Button variant="outline" size="sm" asChild>
              <Link to={`/admin/timetables/${t.id}${editMode ? '' : '/edit'}`}>
                <Pencil /> {editMode ? 'View grid' : 'Edit'}
              </Link>
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => clone.mutate()}
            disabled={clone.isPending}
          >
            <Copy /> {clone.isPending ? 'Cloning…' : 'Clone'}
          </Button>
          {t.status !== 'PUBLISHED' && t.status !== 'ARCHIVED' && (
            <ConfirmDialog
              trigger={
                <Button size="sm" disabled={publish.isPending}>
                  <Megaphone /> {publish.isPending ? 'Publishing…' : 'Publish'}
                </Button>
              }
              title="Publish this timetable?"
              description="Publishing makes this version live for users. The timetable is validated first; same-division published versions are archived automatically. Published timetables cannot be edited."
              confirmLabel="Publish"
              onConfirm={() => publish.mutateAsync()}
            />
          )}
          {t.status !== 'ARCHIVED' && t.status !== 'DRAFT' && (
            <ConfirmDialog
              trigger={
                <Button size="sm" variant="outline" disabled={archive.isPending}>
                  <Archive /> Archive
                </Button>
              }
              title="Archive this timetable?"
              description="Archived timetables are kept as read-only history."
              confirmLabel="Archive"
              onConfirm={() => archive.mutateAsync()}
            />
          )}
        </div>
      </div>

      {!editable && (
        <p className="rounded-md bg-slate-100 px-3 py-2 text-sm text-slate-600">
          This timetable is {t.status} and immutable. Clone it to create an editable DRAFT version.
        </p>
      )}

      <Tabs defaultValue={versionsMode ? 'versions' : 'grid'}>
        <TabsList>
          <TabsTrigger value="grid">Weekly grid</TabsTrigger>
          <TabsTrigger value="validation">Validation</TabsTrigger>
          <TabsTrigger value="versions">Versions</TabsTrigger>
        </TabsList>

        <TabsContent value="grid">
          {periods.isPending && <LoadingState />}
          {periods.isError && (
            <ErrorState message={parseApiError(periods.error).message} onRetry={() => periods.refetch()} />
          )}
          {periods.isSuccess && (
            <TimetableGrid
              periods={periods.data.items}
              entries={t.entries}
              editable={editable && editMode}
              onAdd={openAdd}
              onEdit={openEdit}
            />
          )}
          {editable && editMode && (
            <Card>
              <CardContent className="flex flex-wrap items-center gap-2 pt-5 text-sm text-slate-600">
                <span>
                  Editing sends <code>If-Unmodified-Since</code> automatically — if someone else
                  changed this timetable first, you get a 409 and a refresh instead of an overwrite.
                </span>
                <Badge variant="outline">{t.entries.length} entries</Badge>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="validation">
          <ValidationPanel
            result={report}
            isPending={validation.isPending}
            error={validation.isError ? parseApiError(validation.error).message : null}
            onValidate={() => validate.mutate()}
            validating={validate.isPending || validation.isFetching}
          />
          {validate.isSuccess && validate.data && (
            <p className="mt-2 text-sm text-slate-500">
              Last check: {validate.data.valid ? 'valid' : 'invalid'}
              {validate.data.score !== null && validate.data.score !== undefined
                ? ` · quality score ${validate.data.score}`
                : ''}
              .
            </p>
          )}
        </TabsContent>

        <TabsContent value="versions">
          {versions.isPending && <LoadingState />}
          {versions.isError && (
            <ErrorState message={parseApiError(versions.error).message} onRetry={() => versions.refetch()} />
          )}
          {versions.isSuccess && (
            <div className="grid gap-2">
              {versions.data.items.map((v) => (
                <div
                  key={v.id}
                  className="flex flex-wrap items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm"
                >
                  <Link to={`/admin/timetables/${v.id}`} className="font-medium hover:underline">
                    v{v.version}
                  </Link>
                  <StatusBadge status={v.status} />
                  <span className="text-xs text-slate-500">
                    {v.entry_count} entries · updated {new Date(v.updated_at).toLocaleString()}
                  </span>
                  {v.id !== t.id && (
                    <span className="ml-auto flex gap-2">
                      <Button asChild variant="outline" size="sm">
                        <Link to={`/admin/timetables/${v.id}`}>View</Link>
                      </Button>
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {lastConflicts && (
        <ConflictPanel title={lastConflicts.title} conflicts={lastConflicts.conflicts} />
      )}

      <Dialog
        open={editing !== null || addPeriod !== null}
        onOpenChange={(open) => {
          if (!open) {
            setEditing(null);
            setAddPeriod(null);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? 'Edit entry' : 'Add entry'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit((v) => saveEntry.mutateAsync(v))} className="grid gap-4">
            {entryError && <p className="text-sm text-red-600">{entryError}</p>}
            <Field control={control} name="subject_id" label="Subject" required error={errors.subject_id?.message}>
              {({ value, onChange }) => (
                <OptionSelect label="" kind="subjects" value={(value as string) || undefined} onChange={(v) => onChange(v ?? '')} />
              )}
            </Field>
            <Field control={control} name="faculty_id" label="Faculty" required error={errors.faculty_id?.message}>
              {({ value, onChange }) => (
                <OptionSelect label="" kind="faculty" value={(value as string) || undefined} onChange={(v) => onChange(v ?? '')} />
              )}
            </Field>
            <Field control={control} name="room_id" label="Room" required error={errors.room_id?.message}>
              {({ value, onChange }) => (
                <RoomSelect value={(value as string) || undefined} onChange={(v) => onChange(v ?? '')} />
              )}
            </Field>
            <Field control={control} name="period_id" label="Period" required error={errors.period_id?.message}>
              {({ value, onChange }) => (
                <PeriodSelect
                  value={(value as string) || undefined}
                  onChange={(v) => onChange(v ?? '')}
                  locked={editing === null}
                />
              )}
            </Field>
            <DialogFooter>
              {editing && (
                <ConfirmDialog
                  trigger={
                    <Button type="button" variant="outline" className="mr-auto text-red-600">
                      <Trash2 /> Delete
                    </Button>
                  }
                  title="Delete this entry?"
                  description="The timetable will be revalidated and may become a draft."
                  confirmLabel="Delete"
                  destructive
                  onConfirm={async () => {
                    await removeEntry.mutateAsync(editing.id);
                    setEditing(null);
                  }}
                />
              )}
              <Button type="button" variant="outline" onClick={() => { setEditing(null); setAddPeriod(null); }}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting || saveEntry.isPending}>
                {isSubmitting || saveEntry.isPending ? 'Saving…' : editing ? 'Save changes' : 'Add entry'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
