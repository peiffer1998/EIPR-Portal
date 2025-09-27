import { useEffect, useState } from "react";

type Props = {
  value?: string | null;
  placeholder?: string;
  onSave: (nextValue: string) => Promise<any>;
};

export default function InlineText({ value, placeholder = "", onSave }: Props) {
  const [current, setCurrent] = useState<string>(value ?? "");
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!editing) {
      setCurrent(value ?? "");
    }
  }, [value, editing]);

  if (!editing) {
    return (
      <button
        type="button"
        className="text-left min-w-[120px]"
        onClick={() => {
          setEditing(true);
          setError(null);
        }}
      >
        {current ? current : <span className="text-slate-400">{placeholder}</span>}
      </button>
    );
  }

  const handleSave = async () => {
    try {
      setBusy(true);
      setError(null);
      await onSave(current);
      setEditing(false);
    } catch (err: any) {
      const message = err?.response?.data?.detail || err?.message || "Save failed";
      setError(message);
    } finally {
      setBusy(false);
    }
  };

  const handleCancel = () => {
    setCurrent(value ?? "");
    setEditing(false);
    setError(null);
  };

  return (
    <span className="inline-flex items-center gap-1">
      <input
        className="border rounded px-2 py-1 text-sm"
        value={current}
        onChange={(event) => setCurrent(event.target.value)}
      />
      <button
        type="button"
        className="text-sm bg-slate-900 text-white px-2 py-1 rounded"
        disabled={busy}
        onClick={handleSave}
      >
        {busy ? "Saving…" : "Save"}
      </button>
      <button type="button" className="text-sm px-2 py-1" onClick={handleCancel}>
        Cancel
      </button>
      {error ? <span className="text-xs text-red-600 ml-2 max-w-[160px]">{error}</span> : null}
    </span>
  );
}
