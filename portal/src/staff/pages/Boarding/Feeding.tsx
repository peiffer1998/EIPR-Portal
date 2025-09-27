import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Printer } from "lucide-react";

import BoardFilters from "../../components/BoardFilters";
import BulkBar from "../../components/BulkBar";
import InlineText from "../../components/InlineText";
import StatusBadge from "../../components/StatusBadge";
import { getFeedingBoard, updateFeedingItem } from "../../lib/boardFetchers";

type FilterState = {
  date: string;
  location_id: string;
  area?: string;
  q?: string;
};

type FeedingRow = {
  id: string;
  reservation_id: string;
  pet?: { id?: string; name?: string };
  run?: { id?: string; name?: string };
  time?: string | null;
  food?: string | null;
  amount?: string | null;
  notes?: string | null;
  status?: string | null;
};

export default function FeedingBoard() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<FilterState>({
    date: new Date().toISOString().slice(0, 10),
    location_id: localStorage.getItem("defaultLocationId") || "",
  });
  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const [bulkBusy, setBulkBusy] = useState(false);

  const { data, isFetching } = useQuery({
    queryKey: ["feeding-board", filters.date, filters.location_id],
    queryFn: () => getFeedingBoard(filters.date, filters.location_id),
    enabled: Boolean(filters.date && filters.location_id),
  });

  useEffect(() => {
    setSelected({});
  }, [filters.date, filters.location_id]);

  const rows = useMemo<FeedingRow[]>(() => {
    if (!Array.isArray(data)) return [];
    let list = data as FeedingRow[];
    if (filters.area) {
      const value = filters.area.toLowerCase();
      list = list.filter((row) => (row.run?.name || "").toLowerCase().includes(value));
    }
    if (filters.q) {
      const value = filters.q.toLowerCase();
      list = list.filter(
        (row) =>
          (row.pet?.name || "").toLowerCase().includes(value) ||
          row.reservation_id.toLowerCase().includes(value),
      );
    }
    return list;
  }, [data, filters.area, filters.q]);

  const mutation = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: Record<string, unknown> }) => updateFeedingItem(id, patch),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["feeding-board", filters.date, filters.location_id] });
    },
  });

  const markStatus = (id: string, status: string) => {
    mutation.mutate({ id, patch: { status } });
  };

  const bulkMarkGiven = async () => {
    const ids = Object.entries(selected)
      .filter(([, isSelected]) => isSelected)
      .map(([id]) => id);
    if (ids.length === 0) return;
    setBulkBusy(true);
    try {
      await Promise.all(
        ids.map((id) => updateFeedingItem(id, { status: "GIVEN" }).catch(() => undefined)),
      );
      await queryClient.invalidateQueries({
        queryKey: ["feeding-board", filters.date, filters.location_id],
      });
      setSelected({});
    } finally {
      setBulkBusy(false);
    }
  };

  const toggleSelectAll = (checked: boolean) => {
    if (!checked) {
      setSelected({});
      return;
    }
    const map: Record<string, boolean> = {};
    rows.forEach((row) => {
      map[row.id] = true;
    });
    setSelected(map);
  };

  const goToPrint = () => {
    if (!filters.date || !filters.location_id) return;
    const url = `/staff/print/feeding-sheet/${filters.date}?location_id=${encodeURIComponent(filters.location_id)}`;
    window.open(url, "_blank", "noopener");
  };

  return (
    <div className="grid gap-3">
      <BoardFilters onChange={setFilters} />

      <div className="flex items-center justify-between">
        <div className="text-sm text-slate-600">
          {isFetching ? "Loading…" : `${rows.length} feeding items`}
        </div>
        <button
          type="button"
          className="inline-flex items-center gap-2 bg-slate-900 text-white px-3 py-2 rounded"
          disabled={!filters.location_id || !filters.date}
          onClick={goToPrint}
        >
          <Printer size={16} /> Print sheet
        </button>
      </div>

      <BulkBar selected={selected} busy={bulkBusy} onMarkGiven={bulkMarkGiven} />

      <div className="bg-white rounded-xl shadow overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500">
              <th className="px-3 py-2">
                <input
                  type="checkbox"
                  checked={rows.length > 0 && rows.every((row) => selected[row.id])}
                  onChange={(event) => toggleSelectAll(event.target.checked)}
                />
              </th>
              <th className="px-3 py-2">Pet</th>
              <th>Run</th>
              <th>Time</th>
              <th>Food</th>
              <th>Amount</th>
              <th>Notes</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-t">
                <td className="px-3 py-2">
                  <input
                    type="checkbox"
                    checked={Boolean(selected[row.id])}
                    onChange={(event) =>
                      setSelected((prev) => ({ ...prev, [row.id]: event.target.checked }))
                    }
                  />
                </td>
                <td className="px-3 py-2">{row.pet?.name || row.reservation_id}</td>
                <td>{row.run?.name || ""}</td>
                <td>{row.time || ""}</td>
                <td>
                  <InlineText
                    value={row.food || ""}
                    placeholder="food"
                    onSave={(value) => mutation.mutateAsync({ id: row.id, patch: { food: value } })}
                  />
                </td>
                <td>
                  <InlineText
                    value={row.amount || ""}
                    placeholder="amount"
                    onSave={(value) => mutation.mutateAsync({ id: row.id, patch: { amount: value } })}
                  />
                </td>
                <td>
                  <InlineText
                    value={row.notes || ""}
                    placeholder="notes"
                    onSave={(value) => mutation.mutateAsync({ id: row.id, patch: { notes: value } })}
                  />
                </td>
                <td>
                  <StatusBadge status={row.status || "PENDING"} />
                </td>
                <td className="py-2">
                  <div className="flex gap-2">
                    <button
                      type="button"
                      className="text-xs bg-green-600 text-white px-2 py-1 rounded"
                      onClick={() => markStatus(row.id, "GIVEN")}
                    >
                      Given
                    </button>
                    <button
                      type="button"
                      className="text-xs bg-yellow-600 text-white px-2 py-1 rounded"
                      onClick={() => markStatus(row.id, "SKIPPED")}
                    >
                      Skipped
                    </button>
                    <button
                      type="button"
                      className="text-xs bg-slate-600 text-white px-2 py-1 rounded"
                      onClick={() => markStatus(row.id, "PENDING")}
                    >
                      Pending
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {rows.length === 0 && !isFetching ? (
              <tr>
                <td colSpan={9} className="px-3 py-4 text-sm text-slate-500">
                  No feeding items for this date and location.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
