import { useMemo } from 'react';

const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
});

type TenderBarProps = {
  total: number | string;
  onCash: () => void;
  onCard: () => void;
};

export default function TenderBar({ total, onCash, onCard }: TenderBarProps) {
  const displayTotal = useMemo(() => {
    const numericTotal = typeof total === 'string' ? Number(total) : total;
    if (Number.isFinite(numericTotal)) {
      return currencyFormatter.format(numericTotal as number);
    }
    return currencyFormatter.format(0);
  }, [total]);

  return (
    <div className="flex gap-3 items-center">
      <div className="text-2xl font-bold" aria-live="polite">
        {displayTotal}
      </div>
      <button
        type="button"
        className="px-4 py-3 rounded bg-slate-900 text-white text-lg"
        onClick={onCard}
      >
        Card
      </button>
      <button
        type="button"
        className="px-4 py-3 rounded bg-green-600 text-white text-lg"
        onClick={onCash}
      >
        Cash
      </button>
    </div>
  );
}
