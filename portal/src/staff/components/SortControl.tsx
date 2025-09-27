import React from "react";

export type TabKey = "ARRIVING" | "DEPARTING" | "STAYING" | "REQUESTS";
export type SortKey = "start_asc" | "end_asc" | "run_pet" | "pet_asc";

const DEFAULTS: Record<TabKey, SortKey> = {
  ARRIVING: "start_asc",
  DEPARTING: "end_asc",
  STAYING: "run_pet",
  REQUESTS: "start_asc",
};

const LABELS: Record<SortKey, string> = {
  start_asc: "Start time (earliest)",
  end_asc: "End time (earliest)",
  run_pet: "Run • Pet name",
  pet_asc: "Pet name (A–Z)",
};

const OPTIONS: Record<TabKey, SortKey[]> = {
  ARRIVING: ["start_asc", "pet_asc"],
  DEPARTING: ["end_asc", "pet_asc"],
  STAYING: ["run_pet", "pet_asc"],
  REQUESTS: ["start_asc", "pet_asc"],
};

function storageKey(tab: TabKey) {
  return `staff_dashboard_sort_${tab}`;
}

export function getStoredSort(tab: TabKey): SortKey {
  if (typeof window === "undefined") return DEFAULTS[tab];
  const value = window.localStorage.getItem(storageKey(tab));
  if (value && Object.prototype.hasOwnProperty.call(LABELS, value)) {
    return value as SortKey;
  }
  return DEFAULTS[tab];
}

export default function SortControl({
  tab,
  value,
  onChange,
}: {
  tab: TabKey;
  value: SortKey;
  onChange: (sortKey: SortKey) => void;
}) {
  React.useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(storageKey(tab), value);
  }, [tab, value]);

  return (
    <label className="text-sm font-medium text-slate-700">
      <span className="mb-1 block text-xs uppercase tracking-wide text-slate-500">Sort</span>
      <select
        className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
        value={value}
        onChange={(event) => onChange(event.target.value as SortKey)}
      >
        {OPTIONS[tab].map((option) => (
          <option key={option} value={option}>
            {LABELS[option]}
          </option>
        ))}
      </select>
    </label>
  );
}

export const DEFAULT_SORT = DEFAULTS;
