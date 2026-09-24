import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Pencil, Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { z } from 'zod';
import { ConfirmDialog } from '@/components/common/ConfirmDialog';
import { Field } from '@/components/common/Field';
import { Pagination } from '@/components/common/Pagination';
import { TimeSelect } from '@/components/common/TimeSelect';
import { EmptyState, ErrorState, LoadingState } from '@/components/common/States';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { parseApiError } from '@/services/api';
import type { ListParams } from '@/services/crud';
import type { Page } from '@/types/api';

export interface FieldOption {
  value: string;
  label: string;
}

export interface FieldConfig {
  name: string;
  label: string;
  type: 'text' | 'number' | 'select' | 'checkbox' | 'date' | 'time';
  required?: boolean;
  placeholder?: string;
  hint?: string;
  min?: number;
  step?: string;
  options?: FieldOption[];
  loadOptions?: () => Promise<FieldOption[]>;
  disabledOnEdit?: boolean;
  /** Initial value for the create form (checkboxes default to true otherwise). */
  defaultValue?: unknown;
}

export interface ColumnConfig<T> {
  key: string;
  header: string;
  render: (row: T) => React.ReactNode;
}

function buildSchema(fields: FieldConfig[]) {
  const shape: Record<string, z.ZodTypeAny> = {};
  for (const f of fields) {
    let field: z.ZodTypeAny;
    switch (f.type) {
      case 'number': {
        const min = f.min;
        const label = f.label;
        const required = Boolean(f.required);
        field = z.string().refine(
          (v) =>
            (v.trim() !== '' || !required) &&
            (v.trim() === '' ||
              (Number.isFinite(Number(v)) && (min === undefined || Number(v) >= min))),
          {
            message: required
              ? min !== undefined
                ? `${label} must be a number of at least ${min}`
                : `${label} must be a number`
              : `Must be a number${min !== undefined ? ` of at least ${min}` : ''} or empty`,
          },
        );
        break;
      }
      case 'checkbox':
        field = z.boolean();
        break;
      case 'select':
      case 'date':
      case 'text':
      default:
        field = z.string();
        if (f.required) field = (field as z.ZodString).min(1, `${f.label} is required`);
        break;
      case 'time': {
        // TimeSelect emits "HH:MM"; the API may return "HH:MM:SS".
        const timeRe = /^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$/;
        field = f.required
          ? z.string().regex(timeRe, `${f.label} must be a valid time`)
          : z.string().refine((v) => v === '' || timeRe.test(v), {
              message: `${f.label} must be a valid time`,
            });
        break;
      }
    }
    if (!f.required && f.type !== 'checkbox' && f.type !== 'number') {
      field = field.optional();
    }
    shape[f.name] = field;
  }
  return z.object(shape);
}

type FormValues = Record<string, unknown>;

function cleanPayload(values: FormValues): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(values)) {
    if (v === '' || v === undefined) continue;
    out[k] = v;
  }
  return out;
}

interface CrudPageProps<T extends { id: string }> {
  title: string;
  description?: string;
  entityName: string;
  columns: ColumnConfig<T>[];
  fields: FieldConfig[];
  queryKey: string[];
  list: (params: ListParams) => Promise<Page<T>>;
  createItem?: (body: Record<string, unknown>) => Promise<T>;
  updateItem?: (id: string, body: Record<string, unknown>) => Promise<T>;
  removeItem?: (id: string) => Promise<void>;
  filters?: (params: ListParams, setParams: (p: ListParams) => void) => React.ReactNode;
  defaultParams?: ListParams;
  deleteDescription?: (row: T) => string;
}

export function CrudPage<T extends { id: string }>({
  title,
  description,
  entityName,
  columns,
  fields,
  queryKey,
  list,
  createItem,
  updateItem,
  removeItem,
  filters,
  defaultParams,
  deleteDescription,
}: CrudPageProps<T>) {
  const queryClient = useQueryClient();
  const [params, setParams] = useState<ListParams>({ page: 1, page_size: 20, ...defaultParams });
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<T | null>(null);
  const [optionMaps, setOptionMaps] = useState<Record<string, FieldOption[]>>({});

  const query = useQuery({
    queryKey: [...queryKey, params],
    queryFn: () => list(params),
  });

  const schema = useMemo(() => buildSchema(fields), [fields]);
  type Values = z.infer<typeof schema>;
  const form = useForm<Values>({ resolver: zodResolver(schema) });
  const {
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = form;

  function openCreate() {
    const defaults: FormValues = {};
    for (const f of fields) {
      defaults[f.name] =
        f.defaultValue ?? (f.type === 'checkbox' ? true : f.type === 'number' ? '' : '');
    }
    reset(defaults as Values);
    setEditing(null);
    setDialogOpen(true);
  }

  function openEdit(row: T) {
    const values: FormValues = {};
    for (const f of fields) {
      const v = (row as unknown as Record<string, unknown>)[f.name];
      if (v === undefined || v === null) {
        values[f.name] = f.type === 'checkbox' ? false : '';
      } else if (typeof v === 'number') {
        // Numeric form fields are strings in the form state (converted back
        // to numbers on submit); stringify row values so edits validate.
        values[f.name] = String(v);
      } else if (f.type === 'time' && typeof v === 'string') {
        // API returns "HH:MM:SS"; the picker works with "HH:MM".
        values[f.name] = v.slice(0, 5);
      } else {
        values[f.name] = v;
      }
    }
    reset(values as Values);
    setEditing(row);
    setDialogOpen(true);
  }

  useEffect(() => {
    if (!dialogOpen) return;
    let cancelled = false;
    for (const f of fields) {
      if (!f.loadOptions || optionMaps[f.name]) continue;
      f.loadOptions()
        .then((opts) => {
          if (!cancelled) setOptionMaps((m) => ({ ...m, [f.name]: opts }));
        })
        .catch(() => toast.error(`Could not load options for ${f.label}`));
    }
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dialogOpen]);

  const invalidate = () => queryClient.invalidateQueries({ queryKey });

  const numericFields = useMemo(
    () => new Set(fields.filter((f) => f.type === 'number').map((f) => f.name)),
    [fields],
  );

  const saveMutation = useMutation({
    mutationFn: async (values: FormValues) => {
      const body = cleanPayload(values);
      for (const key of Object.keys(body)) {
        if (numericFields.has(key)) body[key] = Number(body[key]);
      }
      if (editing && updateItem) return updateItem(editing.id, body);
      if (!editing && createItem) return createItem(body);
      throw new Error('Operation not supported');
    },
    onSuccess: () => {
      toast.success(editing ? `${entityName} updated` : `${entityName} created`);
      setDialogOpen(false);
      invalidate();
    },
    onError: (error) => toast.error(parseApiError(error).message),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      if (!removeItem) throw new Error('Delete not supported');
      await removeItem(id);
    },
    onSuccess: () => {
      toast.success(`${entityName} deleted`);
      invalidate();
    },
    onError: (error) => toast.error(parseApiError(error).message),
  });

  const canWrite = Boolean(createItem);
  const rows = query.data?.items ?? [];

  return (
    <div className="grid min-w-0 gap-4 [&>*]:min-w-0">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
          {description && <p className="mt-0.5 text-sm text-slate-500">{description}</p>}
        </div>
        {canWrite && (
          <Button onClick={openCreate}>
            <Plus /> New {entityName}
          </Button>
        )}
      </div>

      {filters?.(params, (p) => setParams({ ...p, page: 1 }))}

      {query.isPending && <LoadingState label={`Loading ${title}`} />}
      {query.isError && (
        <ErrorState message={parseApiError(query.error).message} onRetry={() => query.refetch()} />
      )}
      {query.isSuccess && rows.length === 0 && (
        <EmptyState
          title={`No ${title.toLowerCase()} found`}
          description="Try adjusting filters, or create the first one."
          action={canWrite ? <Button onClick={openCreate}><Plus /> New {entityName}</Button> : undefined}
        />
      )}
      {query.isSuccess && rows.length > 0 && (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                {columns.map((c) => (
                  <TableHead key={c.key}>{c.header}</TableHead>
                ))}
                {(updateItem || removeItem) && <TableHead>Actions</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.id}>
                  {columns.map((c) => (
                    <TableCell key={c.key}>{c.render(row)}</TableCell>
                  ))}
                  {(updateItem || removeItem) && (
                    <TableCell>
                      <div className="flex gap-1">
                        {updateItem && (
                          <Button variant="ghost" size="icon" onClick={() => openEdit(row)} aria-label="Edit">
                            <Pencil />
                          </Button>
                        )}
                        {removeItem && (
                          <ConfirmDialog
                            trigger={
                              <Button variant="ghost" size="icon" aria-label="Delete">
                                <Trash2 className="text-red-600" />
                              </Button>
                            }
                            title={`Delete ${entityName}?`}
                            description={
                              deleteDescription?.(row) ?? 'This action cannot be undone.'
                            }
                            confirmLabel="Delete"
                            destructive
                            onConfirm={() => deleteMutation.mutateAsync(row.id)}
                          />
                        )}
                      </div>
                    </TableCell>
                  )}
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

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editing ? `Edit ${entityName}` : `New ${entityName}`}
            </DialogTitle>
          </DialogHeader>
          <form
            onSubmit={handleSubmit((values) => saveMutation.mutateAsync(values as FormValues))}
            className="grid gap-4"
          >
            {saveMutation.isError && (
              <p className="text-sm text-red-600">{parseApiError(saveMutation.error).message}</p>
            )}
            {fields.map((f) => (
              <Field
                key={f.name}
                control={control}
                name={f.name}
                label={f.label}
                required={f.required}
                hint={f.hint}
                error={(errors as Record<string, { message?: string }>)[f.name]?.message}
              >
                {({ value, onChange }) =>
                  f.type === 'select' ? (
                    <Select
                      value={(value as string) ?? ''}
                      onValueChange={(v) => onChange(v)}
                      disabled={Boolean(editing) && Boolean(f.disabledOnEdit)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder={`Select ${f.label.toLowerCase()}`} />
                      </SelectTrigger>
                      <SelectContent>
                        {(f.options ?? optionMaps[f.name] ?? []).map((o) => (
                          <SelectItem key={o.value} value={o.value}>
                            {o.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : f.type === 'checkbox' ? (
                    <label className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        className="size-4 rounded border-slate-300"
                        checked={Boolean(value)}
                        onChange={(e) => onChange(e.target.checked)}
                      />
                      Enabled
                    </label>
                  ) : f.type === 'time' ? (
                    <TimeSelect
                      value={(value as string) ?? ''}
                      onChange={(v) => onChange(v)}
                      disabled={Boolean(editing) && Boolean(f.disabledOnEdit)}
                    />
                  ) : (
                    <Input
                      type={f.type === 'number' ? 'number' : f.type === 'date' ? 'date' : 'text'}
                      placeholder={f.placeholder}
                      min={f.min}
                      step={f.step}
                      value={(value as string | number) ?? ''}
                      onChange={(e) => onChange(e.target.value)}
                      disabled={Boolean(editing) && Boolean(f.disabledOnEdit)}
                    />
                  )
                }
              </Field>
            ))}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting || saveMutation.isPending}>
                {isSubmitting || saveMutation.isPending ? 'Saving…' : editing ? 'Save changes' : 'Create'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
