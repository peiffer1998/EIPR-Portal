export type BatchBarProps = {
  count: number;
  onAddToCheckout: () => void;
  onCheckIn: () => void;
  onCheckOut: () => void;
  onMoveRun: () => void;
  onPrint: () => void;
};

export default function BatchBar({
  count,
  onAddToCheckout,
  onCheckIn,
  onCheckOut,
  onMoveRun,
  onPrint,
}: BatchBarProps) {
  if (!count) return null;

  return (
    <div className="sticky top-16 z-10 flex items-center justify-between rounded-xl bg-slate-900 px-4 py-3 text-sm text-white shadow-lg">
      <div>
        <span className="font-semibold">{count}</span>
        <span className="ml-1 opacity-75">selected</span>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          className="rounded bg-orange-500 px-3 py-1 font-medium text-white transition hover:bg-orange-600"
          onClick={onAddToCheckout}
        >
          Add to Checkout
        </button>
        <button
          type="button"
          className="rounded bg-emerald-500 px-3 py-1 font-medium text-white transition hover:bg-emerald-600"
          onClick={onCheckIn}
        >
          Check-In
        </button>
        <button
          type="button"
          className="rounded bg-slate-800 px-3 py-1 font-medium text-white transition hover:bg-slate-700"
          onClick={onCheckOut}
        >
          Check-Out
        </button>
        <button
          type="button"
          className="rounded bg-slate-800 px-3 py-1 font-medium text-white transition hover:bg-slate-700"
          onClick={onMoveRun}
        >
          Move Run
        </button>
        <button
          type="button"
          className="rounded bg-slate-800 px-3 py-1 font-medium text-white transition hover:bg-slate-700"
          onClick={onPrint}
        >
          Print
        </button>
      </div>
    </div>
  );
}
