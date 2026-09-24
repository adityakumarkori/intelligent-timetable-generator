import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { roleHome, useAuth } from '@/auth/AuthContext';
import { parseApiError } from '@/services/api';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Field } from '@/components/common/Field';
import { Input } from '@/components/ui/input';

const schema = z.object({
  email: z.string().min(1, 'Email is required').email('Enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
});

type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
  const { login, isAuthenticated, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation() as { state?: { from?: string } };
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: '', password: '' },
  });

  if (isAuthenticated && user) {
    navigate(location.state?.from ?? roleHome(user.role), { replace: true });
    return null;
  }

  async function onSubmit(values: FormValues) {
    setServerError(null);
    try {
      const me = await login(values.email.trim(), values.password);
      navigate(location.state?.from ?? roleHome(me.role), { replace: true });
    } catch (error) {
      setServerError(parseApiError(error).message);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-xl">Timetable Generator</CardTitle>
          <CardDescription>Sign in with your college account.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4" noValidate>
            {serverError && (
              <Alert variant="destructive" title="Sign-in failed">
                {serverError}
              </Alert>
            )}
            <Field control={control} name="email" label="Email" required error={errors.email?.message}>
              {({ value, onChange }) => (
                <Input
                  type="email"
                  autoComplete="username"
                  placeholder="admin@college.edu"
                  value={(value as string) ?? ''}
                  onChange={(e) => onChange(e.target.value)}
                />
              )}
            </Field>
            <Field
              control={control}
              name="password"
              label="Password"
              required
              error={errors.password?.message}
            >
              {({ value, onChange }) => (
                <Input
                  type="password"
                  autoComplete="current-password"
                  placeholder="••••••••"
                  value={(value as string) ?? ''}
                  onChange={(e) => onChange(e.target.value)}
                />
              )}
            </Field>
            <Button type="submit" disabled={isSubmitting} className="w-full">
              {isSubmitting ? 'Signing in…' : 'Sign in'}
            </Button>
            <p className="text-center text-xs text-slate-500">
              Seeded admin login: <code>admin@college.edu</code> · password <code>college123</code>
            </p>
            <p className="text-center text-xs">
              <Link to="/health" className="text-slate-500 underline">
                Backend status
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
