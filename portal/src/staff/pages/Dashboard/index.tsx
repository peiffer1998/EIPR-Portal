import React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import Page from "../../../ui/Page";
import { listReservationsForDate, type DashboardReservation } from "../../lib/dashboardFetchers";
import { checkIn, checkOut, cancelReservation } from "../../lib/reservationOps";
import { getPetVax } from "../../lib/fetchers";
import DotMenu from "../../components/DotMenu";
import IconRow, { type VaccineState } from "../../components/IconRow";

const TODAY = new Date().toISOString().slice(0, 10);

type TabKey = "ARRIVING" | "DEPARTING" | "STAYING" | "REQUESTS";

type CategoryMap = Record<TabKey, DashboardReservation[]>;

function deriveStateFromRecords(records: { name: string; expires_on?: string | null }[]): VaccineState {
  if (!records.length) return "missing";
  const today = new Date();
  const soon = new Date(today);
  soon.setDate(today.getDate() + 30);

  let hasExpiry = false;
  let expiringSoon = false;

  for (const record of records) {
    const expiresValue = record.expires_on;
    if (!expiresValue) continue;
    const expiresDate = new Date(expiresValue);
    if (Number.isNaN(expiresDate.getTime())) continue;
    hasExpiry = true;
    if (expiresDate < today) {
      return "expired";
    }
    if (expiresDate <= soon) {
      expiringSoon = true;
    }
  }

  if (!hasExpiry) return "unknown";
  if (expiringSoon) return "expiring";
  return "ok";
}

function fromInlineVaccination(value?: string | null): VaccineState | undefined {
  if (!value) return undefined;
  const normalized = value.toLowerCase();
  if (normalized.includes("missing")) return "missing";
  if (normalized.includes("expired")) return "expired";
  if (normalized.includes("expiring")) return "expiring";
  if (normalized.includes("ok") || normalized.includes("current")) return "ok";
  return undefined;
}

function sortByTime(rows: DashboardReservation[], key: "start_at" | "end_at") {
  return [...rows].sort((a, b) =>
    (a[key] ?? "").localeCompare(b[key] ?? ""),
  );
}

function sortByPet(rows: DashboardReservation[]) {
  return [...rows].sort((a, b) => {
    const left = (a.pet?.name ?? a.pet?.id ?? "").toLowerCase();
    const right = (b.pet?.name ?? b.pet?.id ?? "").toLowerCase();
    return left.localeCompare(right);
  });
}

function buildCategories(dateISO: string, rows: DashboardReservation[]): CategoryMap {
  const arriving = rows.filter((row) => {
    const startDate = (row.start_at ?? "").slice(0, 10);
    return startDate === dateISO && row.status !== "CANCELED";
  });

  const departing = rows.filter((row) => {
    const endDate = (row.end_at ?? "").slice(0, 10);
    return endDate === dateISO && row.status !== "CANCELED";
  });

  const staying = rows.filter((row) => {
    const startDate = (row.start_at ?? "").slice(0, 10);
    const endDate = (row.end_at ?? "").slice(0, 10);
    if (row.status === "CANCELED") return false;
    if (row.status === "CHECKED_IN") return true;
    return startDate <= dateISO && endDate >= dateISO;
  });

  const requests = rows.filter((row) => {
    if (row.status !== "REQUESTED") return false;
    const startDate = (row.start_at ?? "").slice(0, 10);
    return startDate === dateISO;
  });

  return {
    ARRIVING: sortByTime(arriving, "start_at"),
    DEPARTING: sortByTime(departing, "end_at"),
    STAYING: sortByPet(staying),
    REQUESTS: sortByTime(requests, "start_at"),
  };
}

function TabButton({ active, label, count, onClick }: { active: boolean; label: string; count: number; onClick: () => void; }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium transition ${
        active
          ? "border-b-2 border-slate-900 text-slate-900"
          : "border-b-2 border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700"
      }`}
    >
      {label}
      <span className="ml-1 text-xs text-slate-400">({count})</span>
    </button>
  );
}

function Row({ row, vaccineState, onRefresh }: {
  row: DashboardReservation;
  vaccineState: VaccineState;
  onRefresh: () => Promise<unknown>;
}) {
  const navigate = useNavigate();
  const hasMeds = Array.isArray(row.medication_lines) ? row.medication_lines.length > 0 : Boolean(row.medication_lines);
  const hasFeeding = Array.isArray(row.feeding_lines) ? row.feeding_lines.length > 0 : Boolean(row.feeding_lines);
  const runLabel = row.run_name ?? row.run_id ?? null;

  const handleToggle = async () => {
    try {
      if (row.status === "CHECKED_IN") {
        await checkOut(row.id);
      } else {
        await checkIn(row.id, undefined);
      }
    } finally {
      await onRefresh();
    }
  };

  const handleCancel = async () => {
    const confirmDelete = window.confirm("Cancel this reservation?");
    if (!confirmDelete) return;
    try {
      await cancelReservation(row.id);
    } finally {
      await onRefresh();
    }
  };

  const menuItems = [
    { label: "Edit Reservation", onClick: () => navigate(`/staff/reservations/${row.id}`) },
    {
      label: row.status === "CHECKED_IN" ? "Check-Out" : "Check-In",
      onClick: handleToggle,
      disabled: row.status === "CANCELED" || row.status === "CHECKED_OUT",
    },
    {
      label: "Print Run Card",
      onClick: () => window.open(`/staff/print/run-card/${row.id}`, "_blank", "noopener"),
    },
    {
      label: "Delete Reservation",
      onClick: handleCancel,
      danger: true,
      disabled: row.status === "CANCELED",
    },
  ];

  const petName = row.pet?.name ?? row.pet?.id ?? "Pet";
  const ownerFirst = row.owner?.first_name ?? "";
  const ownerLast = row.owner?.last_name ?? "";
  const ownerName = `${ownerFirst} ${ownerLast}`.trim();
  const subtitle = ownerName ? `${ownerName} • ${row.reservation_type}` : row.reservation_type;

  return (
    <div className="flex items-start justify-between rounded-xl bg-white p-4 shadow-sm transition hover:shadow-md">
      <div className="pr-4">
        <div className="text-lg font-semibold text-slate-900">{petName}</div>
        <div className="text-xs uppercase tracking-wide text-slate-500">{subtitle}</div>
        <IconRow vaccineState={vaccineState} hasMeds={hasMeds} hasFeeding={hasFeeding} runLabel={runLabel} />
      </div>
      <DotMenu items={menuItems} />
    </div>
  );
}

export default function StaffDashboard() {
  const [date, setDate] = React.useState<string>(TODAY);
  const [locationId, setLocationId] = React.useState<string>(() => localStorage.getItem("defaultLocationId") ?? "");
  const [activeTab, setActiveTab] = React.useState<TabKey>("ARRIVING");
  const queryClient = useQueryClient();

  const reservationQuery = useQuery({
    queryKey: ["dashboard-reservations", date, locationId],
    queryFn: () => listReservationsForDate(date, locationId || undefined),
  });

  const data = React.useMemo(() => reservationQuery.data ?? [], [reservationQuery.data]);
  const categories = React.useMemo(() => buildCategories(date, data), [date, data]);

  const [vaxStates, setVaxStates] = React.useState<Record<string, VaccineState>>({});

  React.useEffect(() => {
    const updates: Record<string, VaccineState> = {};
    for (const res of data) {
      const petId = res.pet?.id;
      if (!petId) continue;
      const inline = fromInlineVaccination(res.vaccination_status);
      if (inline && vaxStates[petId] !== inline) {
        updates[petId] = inline;
      }
    }
    if (Object.keys(updates).length) {
      setVaxStates((prev) => ({ ...prev, ...updates }));
    }
  }, [data, vaxStates]);

  React.useEffect(() => {
    const uniquePetIds = Array.from(new Set(data.map((row) => row.pet?.id).filter((id): id is string => Boolean(id))));
    const missing = uniquePetIds.filter((petId) => !vaxStates[petId]);
    if (!missing.length) return;

    let cancelled = false;

    (async () => {
      const entries = await Promise.all(
        missing.map(async (petId) => {
          try {
            const rawRecords = await getPetVax(petId);
            const mappedRecords = (Array.isArray(rawRecords) ? rawRecords : [])
              .map((record: any) => ({
                name: String(record?.vaccine ?? record?.name ?? ""),
                given_on: String(record?.given_on ?? record?.date ?? record?.given ?? "").slice(0, 10),
                expires_on: record?.expires_on ?? record?.expires ?? null,
              }))
              .filter((record) => Boolean(record.name));
            const state = deriveStateFromRecords(mappedRecords);
            return [petId, state] as const;
          } catch (error) {
            console.warn("vaccine status fetch failed", error);
            return [petId, "unknown" as VaccineState] as const;
          }
        }),
      );

      if (!cancelled) {
        const newStates: Record<string, VaccineState> = {};
        for (const [petId, state] of entries) {
          newStates[petId] = state;
        }
        if (Object.keys(newStates).length) {
          setVaxStates((prev) => ({ ...prev, ...newStates }));
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [data, vaxStates]);

  React.useEffect(() => {
    // When the date or location changes, reset to Arriving for clarity
    setActiveTab("ARRIVING");
  }, [date, locationId]);

  const handleRefresh = React.useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: ["dashboard-reservations", date, locationId] });
  }, [queryClient, date, locationId]);

  const currentRows = categories[activeTab] ?? [];

  return (
    <Page>
      <Page.Header title="Dashboard" sub="Arrivals, departures, and requests" />

      <div className="grid gap-4 md:grid-cols-4">
        <div className="rounded-xl bg-white p-4 shadow">
          <p className="text-xs uppercase text-slate-500">Arriving</p>
          <p className="text-3xl font-semibold">{categories.ARRIVING.length}</p>
        </div>
        <div className="rounded-xl bg-white p-4 shadow">
          <p className="text-xs uppercase text-slate-500">Departing</p>
          <p className="text-3xl font-semibold">{categories.DEPARTING.length}</p>
        </div>
        <div className="rounded-xl bg-white p-4 shadow">
          <p className="text-xs uppercase text-slate-500">Staying</p>
          <p className="text-3xl font-semibold">{categories.STAYING.length}</p>
        </div>
        <div className="rounded-xl bg-white p-4 shadow">
          <p className="text-xs uppercase text-slate-500">Requests</p>
          <p className="text-3xl font-semibold">{categories.REQUESTS.length}</p>
        </div>
      </div>

      <div className="rounded-xl bg-white p-4 shadow">
        <div className="grid gap-3 md:grid-cols-[repeat(3,minmax(0,1fr))_auto] md:items-end">
          <label className="text-sm font-medium text-slate-700">
            <span className="mb-1 block text-xs uppercase tracking-wide text-slate-500">Date</span>
            <input
              type="date"
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              value={date}
              onChange={(event) => setDate(event.target.value)}
            />
          </label>
          <label className="text-sm font-medium text-slate-700 md:col-span-2">
            <span className="mb-1 block text-xs uppercase tracking-wide text-slate-500">Location</span>
            <input
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              placeholder="Location UUID (optional)"
              value={locationId}
              onChange={(event) => {
                const value = event.target.value;
                setLocationId(value);
                if (value) {
                  localStorage.setItem("defaultLocationId", value);
                } else {
                  localStorage.removeItem("defaultLocationId");
                }
              }}
            />
          </label>
          <button
            type="button"
            className="justify-self-start rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
            onClick={() => reservationQuery.refetch()}
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="rounded-xl bg-white shadow">
        <div className="flex flex-wrap gap-2 border-b border-slate-200 px-4">
          <TabButton label="Arriving" count={categories.ARRIVING.length} active={activeTab === "ARRIVING"} onClick={() => setActiveTab("ARRIVING")} />
          <TabButton label="Departing" count={categories.DEPARTING.length} active={activeTab === "DEPARTING"} onClick={() => setActiveTab("DEPARTING")} />
          <TabButton label="Staying" count={categories.STAYING.length} active={activeTab === "STAYING"} onClick={() => setActiveTab("STAYING")} />
          <TabButton label="Requests" count={categories.REQUESTS.length} active={activeTab === "REQUESTS"} onClick={() => setActiveTab("REQUESTS")} />
        </div>
        <div className="space-y-3 p-4">
          {reservationQuery.isLoading ? (
            <div className="text-sm text-slate-500">Loading reservations…</div>
          ) : currentRows.length ? (
            currentRows.map((row) => (
              <Row
                key={row.id}
                row={row}
                vaccineState={row.pet?.id ? vaxStates[row.pet.id] ?? "unknown" : "unknown"}
                onRefresh={handleRefresh}
              />
            ))
          ) : (
            <div className="text-sm text-slate-500">No reservations for this view.</div>
          )}
        </div>
      </div>
    </Page>
  );
}
