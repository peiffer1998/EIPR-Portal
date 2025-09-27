import React from "react";
import type { DashboardReservation } from "../lib/dashboardFetchers";
import type { VaccineState } from "./IconRow";
import { listWaitlistOffered } from "../lib/dashboardActions";

export type AlertKind = "unassigned" | "late" | "waitlist" | "vaccines";

export type AlertsRailProps = {
  dateISO: string;
  locationId?: string;
  reservations: DashboardReservation[];
  vaccineStates: Record<string, VaccineState>;
  onFilter: (kind: AlertKind, payload?: unknown) => void;
};

type AlertItem = { id: string; label: string };

type SectionProps = {
  title: string;
  items: AlertItem[];
  onView?: (item: AlertItem) => void;
  emptyLabel?: string;
};

function AlertSection({ title, items, onView, emptyLabel }: SectionProps) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <header className="mb-2 flex items-center justify-between text-sm font-semibold text-slate-800">
        <span>{title}</span>
        <span className="text-xs font-normal text-slate-400">{items.length}</span>
      </header>
      {items.length === 0 ? (
        <p className="text-xs text-slate-500">{emptyLabel ?? "Nothing to show"}</p>
      ) : (
        <ul className="grid gap-2 text-sm text-slate-700">
          {items.slice(0, 12).map((item) => (
            <li key={item.id} className="flex items-center justify-between">
              <span className="truncate" title={item.label}>{item.label}</span>
              {onView ? (
                <button
                  type="button"
                  className="text-xs font-medium text-slate-600 transition hover:text-slate-900"
                  onClick={() => onView(item)}
                >
                  View
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default function AlertsRail({
  dateISO,
  locationId,
  reservations,
  vaccineStates,
  onFilter,
}: AlertsRailProps) {
  const [waitlist, setWaitlist] = React.useState<AlertItem[]>([]);

  const unassigned = React.useMemo(() => (
    reservations
      .filter((res) => res.status === "CHECKED_IN" && (!res.run_id || res.run_id === "UNASSIGN"))
      .map((res) => ({ id: res.id, label: res.pet?.name ?? res.pet?.id ?? res.id }))
  ), [reservations]);

  const latePickups = React.useMemo(() => (
    reservations
      .filter((res) => {
        if (res.status !== "CHECKED_IN") return false;
        if (!res.end_at) return false;
        const end = new Date(res.end_at);
        if (Number.isNaN(end.getTime())) return false;
        return end.getTime() < Date.now();
      })
      .map((res) => ({ id: res.id, label: res.pet?.name ?? res.pet?.id ?? res.id }))
  ), [reservations]);

  const vaccineItems = React.useMemo(() => (
    reservations
      .filter((res) => {
        const petId = res.pet?.id;
        if (!petId) return false;
        const status = vaccineStates[petId];
        return status === "expiring" || status === "expired";
      })
      .map((res) => ({ id: res.id, label: res.pet?.name ?? res.pet?.id ?? res.id }))
  ), [reservations, vaccineStates]);

  React.useEffect(() => {
    let cancelled = false;
    async function loadWaitlist() {
      const entries = await listWaitlistOffered(dateISO, locationId);
      if (cancelled) return;
      setWaitlist(
        entries.map((entry) => ({
          id: entry.id,
          label: entry.pet?.name ?? entry.pet_id ?? entry.id,
        })),
      );
    }
    loadWaitlist();
    return () => {
      cancelled = true;
    };
  }, [dateISO, locationId]);

  return (
    <div className="grid gap-3">
      <AlertSection
        title="Unassigned (Checked-In)"
        items={unassigned}
        emptyLabel="All checked-in guests have runs assigned"
        onView={(item) => onFilter("unassigned", item)}
      />
      <AlertSection
        title="Late Pickups"
        items={latePickups}
        emptyLabel="No late departures"
        onView={(item) => onFilter("late", item)}
      />
      <AlertSection
        title="Waitlist — Offered"
        items={waitlist}
        emptyLabel="No offers pending"
        onView={(item) => onFilter("waitlist", item)}
      />
      <AlertSection
        title="Vaccines Expiring"
        items={vaccineItems}
        emptyLabel="All visible pets are current"
        onView={(item) => onFilter("vaccines", item)}
      />
    </div>
  );
}
