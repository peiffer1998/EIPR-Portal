import type { ReactNode } from 'react';

import { cn } from './cn';

export default function Table({ className, children }: { className?: string; children: ReactNode }) {
  return <table className={cn('w-full text-sm table-sticky', className)}>{children}</table>;
}
