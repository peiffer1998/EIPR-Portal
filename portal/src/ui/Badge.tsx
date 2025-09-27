import type { ReactNode } from 'react';

import { cn } from './cn';

type BadgeVariant = 'default' | 'success' | 'danger' | 'info';

type BadgeProps = {
  children: ReactNode;
  variant?: BadgeVariant;
  className?: string;
};

const variantClasses: Record<BadgeVariant, string> = {
  default: 'bg-slate-100 text-slate-800',
  success: 'bg-green-100 text-green-800',
  danger: 'bg-red-100 text-red-800',
  info: 'bg-blue-100 text-blue-800',
};

export default function Badge({ children, variant = 'default', className }: BadgeProps) {
  return <span className={cn('px-2 py-1 rounded-full text-[11px]', variantClasses[variant], className)}>{children}</span>;
}
