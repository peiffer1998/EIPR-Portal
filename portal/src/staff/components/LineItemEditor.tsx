import { useState } from "react";
import Money from "./Money";

export type Line = {
  id?: string;
  description: string;
  qty: number;
  unit_price: number;
  taxable: boolean;
};

type Props = {
  lines: Line[];
  onAdd: (line: Line) => Promise<void>;
  onUpdate: (id: string, patch: Partial<Line>) => Promise<void>;
  onRemove: (id: string) => Promise<void>;
};

const emptyDraft: Line = { description: "", qty: 1, unit_price: 0, taxable: true };

export default function LineItemEditor({ lines, onAdd, onUpdate, onRemove }: Props) {
  const [draft, setDraft] = useState<Line>(emptyDraft);
  const [busy, setBusy] = useState(false);

  const handleAdd = async () => {
    if (!draft.description.trim()) return;
    setBusy(true);
    try {
      await onAdd(draft);
      setDraft(emptyDraft);
    } finally {
      setBusy(false);
    }
  };

  const handleUpdate = (id: string, patch: Partial<Line>) => {
    if (!id) return;
    void onUpdate(id, patch);
  };

  const handleRemove = async (id?: string) => {
    if (!id) return;
    setBusy(true);
    try {
      await onRemove(id);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="overflow-hidden rounded-xl bg-white shadow">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-slate-500">
            <th className="px-3 py-2">Description</th>
            <th className="px-3 py-2">Qty</th>
            <th className="px-3 py-2">Unit</th>
            <th className="px-3 py-2">Taxable</th>
            <th className="px-3 py-2">Amount</th>
            <th className="px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          {lines.map((line, index) => {
            const amount = (Number(line.qty) || 0) * (Number(line.unit_price) || 0);
            return (
              <tr key={line.id ?? `${line.description}-${index}`} className="border-t">
                <td className="px-3 py-2">
                  <input
                    className="w-full rounded border px-2 py-1"
                    defaultValue={line.description}
                    onBlur={(event) => handleUpdate(line.id ?? "", { description: event.target.value })}
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    className="w-24 rounded border px-2 py-1"
                    type="number"
                    step="1"
                    defaultValue={line.qty}
                    onBlur={(event) => handleUpdate(line.id ?? "", { qty: Number(event.target.value) })}
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    className="w-28 rounded border px-2 py-1"
                    type="number"
                    step="0.01"
                    defaultValue={line.unit_price}
                    onBlur={(event) => handleUpdate(line.id ?? "", { unit_price: Number(event.target.value) })}
                  />
                </td>
                <td className="px-3 py-2 text-center">
                  <input
                    type="checkbox"
                    defaultChecked={line.taxable}
                    onChange={(event) => handleUpdate(line.id ?? "", { taxable: event.target.checked })}
                  />
                </td>
                <td className="px-3 py-2">
                  <Money value={amount} />
                </td>
                <td className="px-3 py-2 text-right">
                  <button type="button" className="text-xs text-red-600" onClick={() => handleRemove(line.id)} disabled={busy}>
                    Remove
                  </button>
                </td>
              </tr>
            );
          })}
          <tr className="border-t bg-slate-50">
            <td className="px-3 py-2">
              <input
                className="w-full rounded border px-2 py-1"
                placeholder="Description"
                value={draft.description}
                onChange={(event) => setDraft((prev) => ({ ...prev, description: event.target.value }))}
              />
            </td>
            <td className="px-3 py-2">
              <input
                className="w-24 rounded border px-2 py-1"
                type="number"
                step="1"
                value={draft.qty}
                onChange={(event) => setDraft((prev) => ({ ...prev, qty: Number(event.target.value) }))}
              />
            </td>
            <td className="px-3 py-2">
              <input
                className="w-28 rounded border px-2 py-1"
                type="number"
                step="0.01"
                value={draft.unit_price}
                onChange={(event) => setDraft((prev) => ({ ...prev, unit_price: Number(event.target.value) }))}
              />
            </td>
            <td className="px-3 py-2 text-center">
              <input
                type="checkbox"
                checked={draft.taxable}
                onChange={(event) => setDraft((prev) => ({ ...prev, taxable: event.target.checked }))}
              />
            </td>
            <td className="px-3 py-2">
              <Money value={(Number(draft.qty) || 0) * (Number(draft.unit_price) || 0)} />
            </td>
            <td className="px-3 py-2 text-right">
              <button
                type="button"
                className="rounded bg-slate-900 px-3 py-1 text-xs text-white"
                onClick={handleAdd}
                disabled={busy}
              >
                Add
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
