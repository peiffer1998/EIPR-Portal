import { useState } from "react";

type Props = {
  open: boolean;
  title?: string;
  message?: string;
  onCancel: () => void;
  onConfirm: () => Promise<void>;
};

export default function ConfirmDialog({ open, title = "Confirm", message, onCancel, onConfirm }: Props) {
  const [busy, setBusy] = useState(false);

  if (!open) return null;

  const handleConfirm = async () => {
    try {
      setBusy(true);
      await onConfirm();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-[400px] rounded-xl bg-white p-4 shadow-xl">
        <h3 className="text-lg font-semibold">{title}</h3>
        <p className="mt-2 text-sm text-slate-600">{message || "Are you sure?"}</p>
        <div className="mt-4 flex justify-end gap-2">
          <button type="button" className="rounded border px-3 py-2" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button
            type="button"
            className="rounded bg-slate-900 px-3 py-2 text-white"
            onClick={handleConfirm}
            disabled={busy}
          >
            {busy ? "Working…" : "Confirm"}
          </button>
        </div>
      </div>
    </div>
  );
}
