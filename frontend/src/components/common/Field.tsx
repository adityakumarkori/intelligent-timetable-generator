import type { ReactNode } from 'react';
import { useId } from 'react';
import { Controller, type Control, type FieldValues, type Path } from 'react-hook-form';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';

export function Field<T extends FieldValues>({
  control,
  name,
  label,
  error,
  hint,
  children,
  required,
}: {
  control: Control<T>;
  name: Path<T>;
  label: string;
  error?: string;
  hint?: string;
  children: (field: { value: unknown; onChange: (v: unknown) => void }) => ReactNode;
  required?: boolean;
}) {
  const id = useId();
  return (
    <div className="grid gap-1.5">
      <Label htmlFor={id}>
        {label} {required && <span className="text-red-600">*</span>}
      </Label>
      <Controller
        control={control}
        name={name}
        render={({ field }) => (
          <div id={id} className={cn(error && '[&_*]:border-red-400')}>
            {children({ value: field.value, onChange: field.onChange })}
          </div>
        )}
      />
      {hint && !error && <p className="text-xs text-slate-500">{hint}</p>}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
