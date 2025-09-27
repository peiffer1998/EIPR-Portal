import React from "react";

import { listRuns } from "../lib/reservationOps";

export type RunPickerProps = {
  open: boolean;
  locationId?: string;
  currentRunId?: string | null;
  occupancy?: Record<string, number>;
  onPick: (runId: string | null) => void;
  onClose: () => void;
};

type RunRecord = {
  id: string;
  name?: string | null;
  kind?: string | null;
  capacity?: number | null;
};

function matchesQuery(run: RunRecord, query: string) {
  if (!query) return true;
  const normalized = query.trim().toLowerCase();
  const name = (run.name ?? "").toLowerCase();
  return name.includes(normalized) || run.id.toLowerCase().includes(normalized);
}

export default function RunPickerModal({
  open,
  locationId,
  currentRunId,
  occupancy,
  onPick,
  onClose,
}: RunPickerProps) {
  const [runs, setRuns] = React.useState<RunRecord[]>([]);
  const [query, setQuery] = React.useState<string>("");
  const [loading, setLoading] = React.useState<boolean>(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!open) return;

    let cancelled = false;
    async function loadRuns() {
      setLoading(true);
      setError(null);
      try {
        const response = await listRuns(locationId);
        if (!cancelled) {
          setRuns(Array.isArray(response) ? response : []);
        }
      } catch (err) {
        console.warn("run picker load failed", err);
        if (!cancelled) {
          setRuns([]);
          setError("Unable to load runs.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadRuns();

    return () => {
      cancelled = true;
    };
  }, [open, locationId]);

  React.useEffect(() => {
    if (!open) {
      setQuery("");
    }
  }, [open]);

  if (!open) return null;

  const filteredRuns = runs.filter((run) => matchesQuery(run, query));
  const occupancyFor = (runId: string) => occupancy?.[runId] ?? 0;

  function handlePick(runId: string | null) {
    onPick(runId);
  }

  return (
    <div className="fixed inset-0 z-40">
      <div
        className="absolute inset-0 bg-slate-900/40"
        role="presentation"
        onClick={onClose}
      />
      <div className="absolute left-1/2 top-[12%] w-full max-w-lg -translate-x-1/2 rounded-xl bg-white p-5 shadow-2xl">
        <header className="mb-3 flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Move to run</p>
            <h2 className="text-lg font-semibold text-slate-900">Select destination</h2>
          </div>
          <button
            type="button"
            className="rounded border border-slate-200 px-3 py-1 text-sm text-slate-600 transition hover:bg-slate-100"
            onClick={onClose}
          >
            Close
          </button>
        </header>

        <label className="mb-3 block text-sm">
          <span className="mb-1 block text-xs uppercase tracking-wide text-slate-500">Search</span>
          <input
            type="search"
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            value={query}
            placeholder="Run name or ID"
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>

        <div className="max-h-[50vh] overflow-y-auto">
          <button
            type="button"
            className={`mb-2 flex w-full flex-col rounded-lg border px-3 py-2 text-left transition hover:bg-slate-50 ${
              !currentRunId ? "border-amber-400 bg-amber-50" : "border-slate-200"
            }`}
            onClick={() => handlePick(null)}
          >
            <span className="text-sm font-semibold text-slate-800">Unassigned</span>
            <span className="text-xs text-slate-500">Remove run assignment</span>
          </button>

          {loading ? (
            <p className="py-4 text-sm text-slate-500">Loading runs…</p>
          ) : error ? (
            <p className="py-4 text-sm text-red-600">{error}</p>
          ) : filteredRuns.length ? (
            <ul className="grid gap-2">
              {filteredRuns.map((run) => {
                const selected = currentRunId === run.id;
                const capacityLabel =
                  run.capacity != null ? `${occupancyFor(run.id)} / ${run.capacity}` : `${occupancyFor(run.id)} assigned`;
                return (
                  <li key={run.id}>
                    <button
                      type="button"
                      className={`flex w-full flex-col rounded-lg border px-3 py-2 text-left transition hover:bg-slate-50 ${
                        selected ? "border-amber-400 bg-amber-50" : "border-slate-200"
                      }`}
                      onClick={() => handlePick(run.id)}
                    >
                      <span className="text-sm font-semibold text-slate-800">{run.name ?? run.id}</span>
                      <span className="text-xs text-slate-500">
                        ID: {run.id}
                        {run.kind ? ` • ${run.kind}` : ""}
                        {` • ${capacityLabel}`}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="py-4 text-sm text-slate-500">No runs match that search.</p>
          )}
        </div>
      </div>
    </div>
  );
}
