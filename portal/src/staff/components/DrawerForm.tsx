import { useEffect, useState } from "react";

type Field = {
  name: string;
  label: string;
  type?: "text" | "number" | "checkbox" | "select";
  placeholder?: string;
  options?: { value: string; label: string }[];
};

interface Props {
  title: string;
  fields: Field[];
  initial?: Record<string, any> | null;
  open: boolean;
  onClose: () => void;
  onSubmit: (vals: Record<string, any>) => Promise<void>;
}

export default function DrawerForm({ title, fields, initial, open, onClose, onSubmit }: Props) {
  const [vals, setVals] = useState<Record<string, any>>({});

  useEffect(() => {
    setVals(initial || {});
  }, [initial, open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/30 z-50">
      <div className="absolute right-0 top-0 h-full w-[440px] bg-white shadow-xl p-4 grid gap-2">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">{title}</h3>
          <button className="text-sm" type="button" onClick={onClose}>
            Close
          </button>
        </div>
        {fields.map((field) => (
          <label key={field.name} className="text-sm grid">
            <span>{field.label}</span>
            {field.type === "checkbox" ? (
              <input
                type="checkbox"
                checked={Boolean(vals[field.name])}
                onChange={(event) =>
                  setVals((prev) => ({ ...prev, [field.name]: event.target.checked }))
                }
              />
            ) : field.type === "select" ? (
              <select
                className="border rounded px-3 py-2"
                value={vals[field.name] ?? ""}
                onChange={(event) =>
                  setVals((prev) => ({ ...prev, [field.name]: event.target.value }))
                }
              >
                <option value="">—</option>
                {(field.options || []).map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            ) : (
              <input
                className="border rounded px-3 py-2"
                type={field.type || "text"}
                placeholder={field.placeholder || ""}
                value={vals[field.name] ?? ""}
                onChange={(event) =>
                  setVals((prev) => ({ ...prev, [field.name]: event.target.value }))
                }
              />
            )}
          </label>
        ))}
        <div className="mt-2 flex justify-end">
          <button
            className="px-3 py-2 rounded bg-slate-900 text-white"
            type="button"
            onClick={() => onSubmit(vals)}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
