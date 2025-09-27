import type { ReactNode } from 'react';

import { cn } from './cn';

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn('card', className)}>{children}</div>;
}

export function CardHeader({
  title,
  sub,
  actions,
}: {
  title: string;
  sub?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between mb-2">
      <div>
        <div className="font-semibold">{title}</div>
        {sub ? <div className="text-sm text-slate-500">{sub}</div> : null}
      </div>
      {actions}
    </div>
  );
}
