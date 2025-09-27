import { useMemo } from "react";

type Props = {
  selected: Record<string, boolean>;
  busy?: boolean;
  onMarkGiven: () => Promise<void>;
};

export default function BulkBar({ selected, busy = false, onMarkGiven }: Props) {
  const count = useMemo(() => Object.values(selected).filter(Boolean).length, [selected]);
  if (count <= 0) return null;

  return (
    <div className="bg-slate-900 text-white px-4 py-2 rounded-xl shadow flex items-center justify-between">
      <div className="text-sm">{count} selected</div>
      <div className="flex gap-2">
        <button
          type="button"
          className="bg-green-600 text-white px-3 py-1 rounded"
          disabled={busy}
          onClick={() => {
            void onMarkGiven();
          }}
        >
          {busy ? "Marking…" : "Mark Given"}
        </button>
      </div>
    </div>
  );
}
