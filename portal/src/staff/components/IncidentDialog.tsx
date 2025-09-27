import { useState } from "react";

type Props = {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: { type: string; note: string }) => Promise<void> | void;
};

const incidentTypes = ["Behavior", "Health", "Owner", "Other"];

export default function IncidentDialog({ open, onClose, onSubmit }: Props) {
  const [type, setType] = useState<string>(incidentTypes[0]);
  const [note, setNote] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  const handleSave = async () => {
    if (!note.trim()) {
      setError("Add a brief note");
      return;
    }
    try {
      setBusy(true);
      setError(null);
      await onSubmit({ type, note: note.trim() });
      setNote("");
      onClose();
    } catch (err: any) {
      setError(err?.message || "Failed to log incident");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <div className="w-full max-w-md rounded-xl bg-white p-5 shadow-xl">
        <h3 className="text-lg font-semibold">Log Incident</h3>
        <p className="mt-1 text-sm text-slate-600">Capture a quick summary for staff follow-up.</p>

        <label className="mt-4 grid text-sm">
          <span className="mb-1 text-slate-600">Type</span>
          <select
            className="rounded border px-3 py-2"
            value={type}
            onChange={(event) => setType(event.target.value)}
          >
            {incidentTypes.map((name) => (
              <option key={name}>{name}</option>
            ))}
          </select>
        </label>

        <label className="mt-3 grid text-sm">
          <span className="mb-1 text-slate-600">Note</span>
          <textarea
            className="min-h-[96px] rounded border px-3 py-2"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Brief notes for the team"
          />
        </label>

        {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}

        <div className="mt-4 flex justify-end gap-2">
          <button type="button" className="rounded border px-3 py-2" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button
            type="button"
            className="rounded bg-slate-900 px-3 py-2 text-white"
            onClick={handleSave}
            disabled={busy}
          >
            {busy ? "Saving…" : "Log incident"}
          </button>
        </div>
      </div>
    </div>
  );
}
