import { ReactNode } from 'react';

type BigButtonProps = {
  label: ReactNode;
  onClick: () => void;
  variant?: 'primary' | 'ghost' | 'danger';
};

const baseClasses = 'rounded-xl px-6 py-8 text-xl font-semibold shadow w-full text-left focus:outline-none focus:ring-2 focus:ring-offset-2';

const variants: Record<NonNullable<BigButtonProps['variant']>, string> = {
  primary: 'bg-orange-500 hover:bg-orange-600 text-white focus:ring-orange-500',
  ghost: 'bg-white hover:bg-slate-50 text-slate-900 border border-slate-300 focus:ring-slate-400',
  danger: 'bg-red-600 hover:bg-red-700 text-white focus:ring-red-500',
};

export default function BigButton({ label, onClick, variant = 'primary' }: BigButtonProps) {
  return (
    <button type="button" onClick={onClick} className={`${baseClasses} ${variants[variant]}`}>
      {label}
    </button>
  );
}
