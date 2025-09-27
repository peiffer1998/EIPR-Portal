import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import BoardFilters from "../../components/BoardFilters";
import { addBelonging, getBelongings, setBelongingReturned } from "../../lib/boardFetchers";

type FilterState = {
  date: string;
  location_id: string;
  area?: string;
  q?: string;
};

type BelongingRow = {
  id: string;
  reservation_id: string;
  pet?: { id?: string; name?: string };
  run?: { id?: string; name?: string };
  name: string;
  note?: string | null;
  returned?: boolean;
};

const initialDraft = { reservation_id: "", name: "", note: "" };

export default function BelongingsBoard() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<FilterState>({
    date: new Date().toISOString().slice(0, 10),
    location_id: localStorage.getItem("defaultLocationId") || "",
  });
  const [draft, setDraft] = useState(initialDraft);

  const { data, isFetching } = useQuery({
    queryKey: ["belongings-board", filters.date, filters.location_id],
    queryFn: () => getBelongings(filters.date, filters.location_id),
    enabled: Boolean(filters.date && filters.location_id),
  });

  const rows = useMemo<BelongingRow[]>(() => {
    if (!Array.isArray(data)) return [];
    let list = data as BelongingRow[];
    if (filters.area) {
      const value = filters.area.toLowerCase();
      list = list.filter((row) => (row.run?.name || "").toLowerCase().includes(value));
    }
    if (filters.q) {
      const value = filters.q.toLowerCase();
      list = list.filter(
        (row) =>
          (row.pet?.name || "").toLowerCase().includes(value) ||
          row.reservation_id.toLowerCase().includes(value) ||
          row.name.toLowerCase().includes(value),
      );
    }
    return list;
  }, [data, filters.area, filters.q]);

  const createMutation = useMutation({
    mutationFn: (payload: typeof initialDraft) => addBelonging(payload.reservation_id, { name: payload.name, note: payload.note || undefined }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["belongings-board", filters.date, filters.location_id] });
    },
  });

  const returnedMutation = useMutation({
    mutationFn: ({ id, returned }: { id: string; returned: boolean }) => setBelongingReturned(id, returned),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["belongings-board", filters.date, filters.location_id] });
    },
  });

  const handleAdd = () => {
    if (!draft.reservation_id || !draft.name) return;
    createMutation.mutate(draft);
    setDraft(initialDraft);
  };

  return (
    <div className="grid gap-3">
      <BoardFilters onChange={setFilters} />

      <div className="bg-white p-4 rounded-xl shadow grid md:grid-cols-4 gap-2 items-end">
        <label className="text-sm grid">
          <span className="text-slate-600">Reservation ID</span>
          <input
            className="border rounded px-3 py-2"
            value={draft.reservation_id}
            onChange={(event) => setDraft((prev) => ({ ...prev, reservation_id: event.target.value }))}
            placeholder="UUID"
          />
        </label>
        <label className="text-sm grid">
          <span className="text-slate-600">Item name</span>
          <input
            className="border rounded px-3 py-2"
            value={draft.name}
            onChange={(event) => setDraft((prev) => ({ ...prev, name: event.target.value }))}
            placeholder="e.g. Blanket"
          />
        </label>
        <label className="text-sm grid">
          <span className="text-slate-600">Note</span>
          <input
            className="border rounded px-3 py-2"
            value={draft.note}
            onChange={(event) => setDraft((prev) => ({ ...prev, note: event.target.value }))}
            placeholder="Optional notes"
          />
        </label>
        <button
          type="button"
          className="bg-slate-900 text-white px-3 py-2 rounded"
          disabled={!draft.reservation_id || !draft.name || createMutation.isPending}
          onClick={handleAdd}
        >
          {createMutation.isPending ? "Adding…" : "Add item"}
        </button>
      </div>

      <div className="bg-white rounded-xl shadow overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500">
              <th className="px-3 py-2">Pet</th>
              <th>Run</th>
              <th>Item</th>
              <th>Note</th>
              <th>Returned</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-t">
                <td className="px-3 py-2">{row.pet?.name || row.reservation_id}</td>
                <td>{row.run?.name || ""}</td>
                <td>{row.name}</td>
                <td>{row.note || ""}</td>
                <td>
                  <label className="inline-flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={Boolean(row.returned)}
                      onChange={(event) =>
                        returnedMutation.mutate({ id: row.id, returned: event.target.checked })
                      }
                    />
                    {row.returned ? "Yes" : "No"}
                  </label>
                </td>
              </tr>
            ))}
            {rows.length === 0 && !isFetching ? (
              <tr>
                <td colSpan={5} className="px-3 py-4 text-sm text-slate-500">
                  No belongings recorded for this date and location.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
