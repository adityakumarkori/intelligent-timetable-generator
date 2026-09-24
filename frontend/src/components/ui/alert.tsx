import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { AlertTriangle, CheckCircle2, Info, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

const alertVariants = cva('relative flex gap-3 rounded-lg border p-4 text-sm', {
  variants: {
    variant: {
      default: 'border-slate-200 bg-white text-slate-800',
      info: 'border-blue-200 bg-blue-50 text-blue-900',
      success: 'border-green-200 bg-green-50 text-green-900',
      warning: 'border-amber-200 bg-amber-50 text-amber-900',
      destructive: 'border-red-200 bg-red-50 text-red-900',
    },
  },
  defaultVariants: { variant: 'default' },
});

const icons = {
  default: Info,
  info: Info,
  success: CheckCircle2,
  warning: AlertTriangle,
  destructive: XCircle,
} as const;

export interface AlertProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {
  title?: string;
}

export function Alert({ className, variant = 'default', title, children, ...props }: AlertProps) {
  const Icon = icons[variant ?? 'default'];
  return (
    <div role="alert" className={cn(alertVariants({ variant }), className)} {...props}>
      <Icon className="mt-0.5 size-4 shrink-0" aria-hidden />
      <div className="min-w-0">
        {title && <p className="font-semibold">{title}</p>}
        <div className="mt-0.5">{children}</div>
      </div>
    </div>
  );
}
