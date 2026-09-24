import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { CheckCircle2, Cpu } from 'lucide-react';
import { toast } from 'sonner';
import { z } from 'zod';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Field } from '@/components/common/Field';
import { Input } from '@/components/ui/input';
import { ConflictPanel } from '@/components/timetable/ConflictPanel';
import { OptionSelect } from '@/components/common/OptionSelect';
import { parseApiError } from '@/services/api';
import { timetableApi } from '@/services/timetableApi';
import type { GenerationFailure, GenerationSuccess } from '@/types/api';

const schema = z.object({
  academic_session_id: z.string().min(1, 'Academic session is required'),
  division_id: z.string().min(1, 'Division is required'),
  time_limit_seconds: z
    .string()
    .refine(
      (v) => {
        const n = Number(v);
        return v.trim() !== '' && Number.isFinite(n) && n >= 5 && n <= 300;
      },
      { message: 'Enter a limit between 5 and 300 seconds' },
    ),
  optimize: z.boolean(),
});

type FormValues = z.infer<typeof schema>;

function isSuccess(
  result: GenerationSuccess | GenerationFailure,
): result is GenerationSuccess {
  return result.status === 'SUCCESS';
}

export default function GeneratePage() {
  const [result, setResult] = useState<GenerationSuccess | GenerationFailure | null>(null);

  const { control, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { academic_session_id: '', division_id: '', time_limit_seconds: '30', optimize: true },
  });

  const generate = useMutation({
    mutationFn: (v: FormValues) =>
      timetableApi.generate(v.academic_session_id, v.division_id, {
        optimize: v.optimize,
        time_limit_seconds: Number(v.time_limit_seconds),
        num_workers: null,
        random_seed: null,
      }),
    onSuccess: (res) => {
      setResult(res);
      if (res.status === 'SUCCESS') toast.success('Timetable generated');
    },
    onError: (error) => toast.error(parseApiError(error).message),
  });

  return (
    <div className="grid max-w-3xl gap-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Generate timetable</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          The CP-SAT engine turns the division&apos;s weekly requirements into scheduled
          sessions, honoring hard constraints and optimizing soft preferences.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Generation scope</CardTitle>
          <CardDescription>
            Requirements, assignments, rooms, and availability are read from the current
            configuration at solve time.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={handleSubmit((v) => {
              setResult(null);
              return generate.mutateAsync(v);
            })}
            className="grid gap-4"
          >
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
            <Field
              control={control}
              name="division_id"
              label="Division"
              required
              error={errors.division_id?.message}
            >
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
            <div className="grid gap-4 sm:grid-cols-2">
              <Field
                control={control}
                name="time_limit_seconds"
                label="Solver time limit (s)"
                error={errors.time_limit_seconds?.message}
              >
                {({ value, onChange }) => (
                  <Input
                    type="number"
                    min={5}
                    max={300}
                    value={(value as number | string) ?? ''}
                    onChange={(e) => onChange(e.target.value)}
                  />
                )}
              </Field>
              <Field control={control} name="optimize" label="Optimize soft preferences">
                {({ value, onChange }) => (
                  <label className="flex h-9 items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      className="size-4 rounded border-slate-300"
                      checked={Boolean(value)}
                      onChange={(e) => onChange(e.target.checked)}
                    />
                    Rank solutions by quality
                  </label>
                )}
              </Field>
            </div>
            <div>
              <Button type="submit" disabled={isSubmitting || generate.isPending}>
                <Cpu />
                {isSubmitting || generate.isPending ? 'Generating… this can take a while' : 'Generate timetable'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {generate.isPending && (
        <Alert variant="info" title="Generating…">
          Please wait while the scheduling engine searches for a feasible timetable. Larger
          configurations can take up to the time limit above.
        </Alert>
      )}
      {generate.isError && (
        <Alert variant="destructive" title="Generation failed to run">
          {parseApiError(generate.error).message}
        </Alert>
      )}

      {result && isSuccess(result) && (
        <Alert variant="success" title="Timetable generated">
          <dl className="mt-2 grid grid-cols-2 gap-x-6 gap-y-1 text-sm">
            <dt className="text-slate-500">Status</dt>
            <dd className="font-medium">GENERATED</dd>
            <dt className="text-slate-500">Solver</dt>
            <dd className="font-medium">{result.solver_status}</dd>
            <dt className="text-slate-500">Quality score</dt>
            <dd className="font-medium tabular-nums">{result.objective_score ?? '—'}</dd>
            <dt className="text-slate-500">Solve time</dt>
            <dd className="font-medium tabular-nums">{(result.generation_duration_ms / 1000).toFixed(1)}s</dd>
          </dl>
          {result.warnings.length > 0 && (
            <ul className="mt-2 list-disc pl-5 text-sm">
              {result.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}
          <div className="mt-3 flex gap-2">
            <Button asChild size="sm">
              <Link to={`/admin/timetables/${result.timetable_id}`}>
                <CheckCircle2 /> View timetable
              </Link>
            </Button>
          </div>
        </Alert>
      )}

      {result && !isSuccess(result) && (
        <ConflictPanel conflicts={result.conflicts} suggestions={result.suggestions} />
      )}
    </div>
  );
}
