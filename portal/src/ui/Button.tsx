import type { ElementType, HTMLAttributes } from 'react';

import { cn } from './cn';

export type ButtonProps = {
  as?: ElementType;
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
} & HTMLAttributes<HTMLElement>;

export default function Button({
  as: Component = 'button',
  variant = 'primary',
  className,
  ...rest
}: ButtonProps) {
  const variants = {
    primary: 'btn-primary',
    secondary: 'btn-secondary',
    ghost: 'btn-ghost',
    danger: 'btn-danger',
  } as const;

  return (
    <Component
      className={cn('btn', variants[variant], className)}
      {...rest}
    />
  );
}
