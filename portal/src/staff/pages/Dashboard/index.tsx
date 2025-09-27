import React from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import Page from "../../../ui/Page";
import {
  listReservationsForDate,
  type DashboardReservation,
} from "../../lib/dashboardFetchers";
import {
  checkIn,
  checkOut,
  cancelReservation,
  moveRun,
} from "../../lib/reservationOps";
import { getPetVax } from "../../lib/fetchers";
import DotMenu from "../../components/DotMenu";
import IconRow, { type VaccineState } from "../../components/IconRow";
import BatchBar from "../../components/BatchBar";
import DrawerReservation from "../../components/DrawerReservation";
import AlertsRail, { type AlertKind } from "../../components/AlertsRail";
import RunPickerModal from "../../components/RunPickerModal";
import ForecastMini from "../../components/ForecastMini";
import SortControl, { type SortKey, getStoredSort } from "../../components/SortControl";
import { useCheckoutCart } from "../../state/CheckoutCart";
import type { CheckoutCartItem } from "../../state/CheckoutCart";
import VirtualList from "../../components/VirtualList";
import LiveIndicator from "../../components/LiveIndicator";
import { toast } from "../../../ui/Toast";

const TODAY = new Date().toISOString().slice(0, 10);
const ROW_HEIGHT = 112;
const LIST_HEIGHT = 560;

type TabKey = "ARRIVING" | "DEPARTING" | "STAYING" | "REQUESTS";

type CategoryMap = Record<TabKey, DashboardReservation[]>;

type VaccinationRecord = { name: string; expires_on?: string | null };

type RowProps = {
  row: DashboardReservation;
  vaccineState: VaccineState;
  onRefresh: () => Promise<unknown>;
  checked: boolean;
  onToggleSelection: (row: DashboardReservation, event: React.ChangeEvent<HTMLInputElement>) => void;
  onOpenDrawer: (row: DashboardReservation) => void;
  onOpenRunPicker: (row: DashboardReservation) => void;
  onAddToCheckout: (row: DashboardReservation) => void;
  onToggleStatus: (row: DashboardReservation) => Promise<void> | void;
  isFocused: boolean;
};

function deriveStateFromRecords(records: VaccinationRecord[]): VaccineState {
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
  return [...rows].sort((a, b) => (a[key] ?? "").localeCompare(b[key] ?? ""));
}

function sortByPet(rows: DashboardReservation[]) {
  return [...rows].sort((a, b) => {
    const left = (a.pet?.name ?? a.pet?.id ?? "").toLowerCase();
    const right = (b.pet?.name ?? b.pet?.id ?? "").toLowerCase();
    return left.localeCompare(right);
  });
}


function normalizeLower(value?: string | null) {
  return (value ?? "").toLowerCase();
}

function sortRows(rows: DashboardReservation[], sortKey: SortKey): DashboardReservation[] {
  const result = [...rows];
  const byStart = (row: DashboardReservation) => row.start_at ?? "";
  const byEnd = (row: DashboardReservation) => row.end_at ?? "";
  const byRun = (row: DashboardReservation) => row.run_name ?? row.run_id ?? "zzz";
  const byPet = (row: DashboardReservation) => normalizeLower(row.pet?.name ?? row.pet?.id ?? "");

  result.sort((a, b) => {
    if (sortKey === "start_asc") return byStart(a).localeCompare(byStart(b));
    if (sortKey === "end_asc") return byEnd(a).localeCompare(byEnd(b));
    if (sortKey === "run_pet") {
      const runCompare = byRun(a).localeCompare(byRun(b));
      if (runCompare !== 0) return runCompare;
      return byPet(a).localeCompare(byPet(b));
    }
    if (sortKey === "pet_asc") return byPet(a).localeCompare(byPet(b));
    return 0;
  });

  return result;
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

function TabButton({
  active,
  label,
  count,
  onClick,
}: {
  active: boolean;
  label: string;
  count: number;
  onClick: () => void;
}) {
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

function Row({
  row,
  vaccineState,
  onRefresh,
  checked,
  onToggleSelection,
  onOpenDrawer,
  onOpenRunPicker,
  onAddToCheckout,
  onToggleStatus,
  isFocused,
}: RowProps) {
  const navigate = useNavigate();
  const hasMeds = Array.isArray(row.medication_lines)
    ? row.medication_lines.length > 0
    : Boolean(row.medication_lines);
  const hasFeeding = Array.isArray(row.feeding_lines)
    ? row.feeding_lines.length > 0
    : Boolean(row.feeding_lines);
  const runLabel = row.run_name ?? row.run_id ?? null;
  const ownerId = row.owner?.id ?? row.owner_id ?? "";
  const canAddToCheckout = Boolean(ownerId);

  const handleToggleStatus = async () => {
    await onToggleStatus(row);
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
      onClick: handleToggleStatus,
      disabled: row.status === "CANCELED" || row.status === "CHECKED_OUT",
    },
    {
      label: "Move to Run",
      onClick: () => onOpenRunPicker(row),
      disabled: row.status === "CANCELED",
    },
    {
      label: "Add to Checkout",
      onClick: () => {
        if (!ownerId) {
          toast("Cannot add reservation without owner details.", "error");
          return;
        }
        onAddToCheckout(row);
      },
      disabled: !canAddToCheckout,
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
    <div
      id={`dashboard-row-${row.id}`}
      role="button"
      tabIndex={0}
      onClick={() => onOpenDrawer(row)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onOpenDrawer(row);
        }
      }}
      className={`flex items-start justify-between rounded-xl border bg-white p-4 shadow-sm transition hover:shadow-md focus:outline-none focus:ring-2 focus:ring-slate-400 ${
        isFocused ? "ring-2 ring-amber-400" : "border-slate-200"
      }`}
    >
      <div className="flex items-start gap-3 pr-4">
        <input
          type="checkbox"
          className="mt-1 h-4 w-4"
          checked={checked}
          onClick={(event) => event.stopPropagation()}
          onChange={(event) => onToggleSelection(row, event)}
        />
        <div className="cursor-pointer select-none">
          <div className="text-lg font-semibold text-slate-900">{petName}</div>
          <div className="text-xs uppercase tracking-wide text-slate-500">{subtitle}</div>
          <IconRow
            vaccineState={vaccineState}
            hasMeds={hasMeds}
            hasFeeding={hasFeeding}
            runLabel={runLabel ?? undefined}
          />
        </div>
      </div>
      <div onClick={(event) => event.stopPropagation()}>
        <DotMenu items={menuItems} />
      </div>
    </div>
  );
}

export default function StaffDashboard() {
  const { add, addMany } = useCheckoutCart();
  const [date, setDate] = React.useState<string>(TODAY);
  const [locationId, setLocationId] = React.useState<string>(
    () => localStorage.getItem("defaultLocationId") ?? "",
  );
  const [activeTab, setActiveTab] = React.useState<TabKey>("ARRIVING");
  const [selection, setSelection] = React.useState<Record<string, boolean>>({});
  const [drawerId, setDrawerId] = React.useState<string | null>(null);
  const [runPicker, setRunPicker] = React.useState<{ ids: string[]; currentRunId?: string | null; locationId?: string | null } | null>(null);
  const [focusIndex, setFocusIndex] = React.useState<number>(0);
  const [lastClickedIndex, setLastClickedIndex] = React.useState<number | null>(null);
  const [lastUpdated, setLastUpdated] = React.useState<Date | null>(null);
  const [sortBy, setSortBy] = React.useState<Record<TabKey, SortKey>>(() => ({
    ARRIVING: getStoredSort("ARRIVING"),
    DEPARTING: getStoredSort("DEPARTING"),
    STAYING: getStoredSort("STAYING"),
    REQUESTS: getStoredSort("REQUESTS"),
  }));
  const queryClient = useQueryClient();

  const reservationQuery = useQuery({
    queryKey: ["dashboard-reservations", date, locationId],
    queryFn: () => listReservationsForDate(date, locationId || undefined),
  });

  React.useEffect(() => {
    if (reservationQuery.data) {
      setLastUpdated(new Date());
    }
  }, [reservationQuery.data]);

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
    const uniquePetIds = Array.from(
      new Set(
        data
          .map((row) => row.pet?.id)
          .filter((id): id is string => Boolean(id)),
      ),
    );
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
    setActiveTab("ARRIVING");
    setFocusIndex(0);
    setLastClickedIndex(null);
  }, [date, locationId]);

  React.useEffect(() => {
    setSelection((prev) => {
      const next: Record<string, boolean> = {};
      for (const res of data) {
        if (prev[res.id]) next[res.id] = true;
      }
      return next;
    });
  }, [data]);

  const refetchReservations = reservationQuery.refetch;
  React.useEffect(() => {
    const interval = window.setInterval(() => {
      if (document.visibilityState === 'visible') {
        refetchReservations();
      }
    }, 45000);
    return () => window.clearInterval(interval);
  }, [refetchReservations]);

  const drawerReservation = React.useMemo(
    () => (drawerId ? data.find((row) => row.id === drawerId) ?? null : null),
    [data, drawerId],
  );

  const handleRefresh = React.useCallback(async () => {
    const result = await reservationQuery.refetch();
    if (!result.error) {
      setLastUpdated(new Date());
    }
  }, [reservationQuery]);

  const currentSort = sortBy[activeTab];
  const currentRows = React.useMemo(() => sortRows(categories[activeTab] ?? [], currentSort), [categories, activeTab, currentSort]);
  const list = currentRows;

  const queryKey = React.useMemo(() => ["dashboard-reservations", date, locationId] as const, [date, locationId]);

  const updateReservationInCache = React.useCallback((id: string, updater: (reservation: DashboardReservation) => DashboardReservation) => {
    queryClient.setQueryData<DashboardReservation[]>(queryKey, (old) => {
      if (!old) return old;
      return old.map((item) => (item.id === id ? updater(item) : item));
    });
  }, [queryClient, queryKey]);

  const occupancy = React.useMemo(() => {
    const counts: Record<string, number> = {};
    for (const reservation of data) {
      if (!reservation.run_id) continue;
      if (reservation.status !== "CHECKED_IN") continue;
      counts[reservation.run_id] = (counts[reservation.run_id] ?? 0) + 1;
    }
    return counts;
  }, [data]);

  const setReservationStatusOptimistic = React.useCallback(async (reservation: DashboardReservation, nextStatus: "CHECKED_IN" | "CHECKED_OUT") => {
    const snapshotRaw = queryClient.getQueryData<DashboardReservation[]>(queryKey);
    const snapshot = snapshotRaw ? snapshotRaw.map((item) => ({ ...item })) : undefined;

    updateReservationInCache(reservation.id, (item) => ({ ...item, status: nextStatus }));

    try {
      if (nextStatus === "CHECKED_IN") {
        await checkIn(reservation.id, reservation.run_id ?? undefined);
      } else {
        await checkOut(reservation.id);
      }
    } catch (error) {
      queryClient.setQueryData(queryKey, snapshot);
      toast("Unable to update reservation status. Changes were reverted.", "error");
      throw error;
    }
  }, [queryClient, queryKey, updateReservationInCache]);

  const toggleReservationStatus = React.useCallback(async (reservation: DashboardReservation) => {
    const nextStatus = reservation.status === "CHECKED_IN" ? "CHECKED_OUT" : "CHECKED_IN";
    await setReservationStatusOptimistic(reservation, nextStatus);
    const petName = reservation.pet?.name ?? 'reservation';
    toast(`${petName} ${nextStatus === 'CHECKED_IN' ? 'checked in' : 'checked out'}`, 'success');
  }, [setReservationStatusOptimistic]);

  const setReservationRunOptimistic = React.useCallback(async (reservation: DashboardReservation, nextRunId: string | null) => {
    const snapshotRaw = queryClient.getQueryData<DashboardReservation[]>(queryKey);
    const snapshot = snapshotRaw ? snapshotRaw.map((item) => ({ ...item })) : undefined;

    updateReservationInCache(reservation.id, (item) => ({
      ...item,
      run_id: nextRunId,
      run_name: nextRunId === item.run_id ? item.run_name : null,
    }));

    try {
      await moveRun(reservation.id, nextRunId ?? null);
    } catch (error) {
      queryClient.setQueryData(queryKey, snapshot);
      toast("Unable to move reservation to the selected run.", "error");
      throw error;
    }
  }, [queryClient, queryKey, updateReservationInCache]);


  const handleToggleSelection = React.useCallback((reservation: DashboardReservation, event: React.ChangeEvent<HTMLInputElement>) => {
    const index = list.findIndex((item) => item.id === reservation.id);
    if (index === -1) return;
    const isShift = event.nativeEvent.shiftKey;
    setSelection((prev) => {
      if (isShift && lastClickedIndex !== null) {
        const next = { ...prev };
        const start = Math.min(lastClickedIndex, index);
        const end = Math.max(lastClickedIndex, index);
        for (let i = start; i <= end; i += 1) {
          next[list[i].id] = true;
        }
        return next;
      }
      const next = { ...prev };
      if (next[reservation.id]) {
        delete next[reservation.id];
      } else {
        next[reservation.id] = true;
      }
      return next;
    });
    setLastClickedIndex(index);
    setFocusIndex(index);
  }, [list, lastClickedIndex]);

  const selectedIds = React.useMemo(
    () => list.filter((res) => selection[res.id]).map((res) => res.id),
    [list, selection],
  );

  React.useEffect(() => {
    if (!list.length) {
      setFocusIndex(0);
      setLastClickedIndex(null);
      return;
    }
    setFocusIndex((prev) => Math.min(Math.max(prev, 0), list.length - 1));
  }, [list.length]);

  React.useEffect(() => {
    setFocusIndex(0);
    setLastClickedIndex(null);
  }, [activeTab]);

  const clearSelection = React.useCallback(() => {
    setSelection({});
    setLastClickedIndex(null);
  }, []);

  const handleBatchCheckIn = React.useCallback(async () => {
    const reservationsToUpdate = list.filter((row) => selectedIds.includes(row.id));
    await Promise.all(
      reservationsToUpdate.map((reservation) =>
        setReservationStatusOptimistic(reservation, "CHECKED_IN").catch(() => undefined),
      ),
    );
    if (reservationsToUpdate.length) {
      toast(`Checked in ${reservationsToUpdate.length} reservation${reservationsToUpdate.length === 1 ? '' : 's'}`, "success");
    }
    clearSelection();
  }, [list, selectedIds, setReservationStatusOptimistic, clearSelection]);

  const handleBatchCheckOut = React.useCallback(async () => {
    const reservationsToUpdate = list.filter((row) => selectedIds.includes(row.id));
    await Promise.all(
      reservationsToUpdate.map((reservation) =>
        setReservationStatusOptimistic(reservation, "CHECKED_OUT").catch(() => undefined),
      ),
    );
    if (reservationsToUpdate.length) {
      toast(`Checked out ${reservationsToUpdate.length} reservation${reservationsToUpdate.length === 1 ? '' : 's'}`, "success");
    }
    clearSelection();
  }, [list, selectedIds, setReservationStatusOptimistic, clearSelection]);

  const handleBatchMoveRun = React.useCallback(() => {
    if (!selectedIds.length) return;
    const firstRow = data.find((row) => row.id === selectedIds[0]);
    const currentRun = selectedIds.length === 1 ? firstRow?.run_id ?? null : null;
    const derivedLocation = firstRow?.location_id ?? (locationId || null);
    setRunPicker({ ids: selectedIds, currentRunId: currentRun, locationId: derivedLocation ?? null });
  }, [selectedIds, data, locationId]);

  const handleBatchPrint = React.useCallback(() => {
    for (const id of selectedIds) {
      window.open(`/staff/print/run-card/${id}`, "_blank", "noopener");
    }
  }, [selectedIds]);

  const selectAllInTab = React.useCallback(() => {
    if (!list.length) return;
    const next: Record<string, boolean> = {};
    list.forEach((reservation) => {
      next[reservation.id] = true;
    });
    setSelection(next);
    setLastClickedIndex(list.length - 1);
    setFocusIndex((prev) => (list.length ? Math.min(prev, list.length - 1) : 0));
  }, [list]);

  const buildCartItem = React.useCallback((reservation: DashboardReservation): CheckoutCartItem | null => {
    const ownerId = reservation.owner?.id ?? reservation.owner_id ?? "";
    if (!ownerId) return null;
    return {
      reservationId: reservation.id,
      ownerId,
      petName: reservation.pet?.name,
      petId: reservation.pet?.id,
      service: reservation.reservation_type,
    };
  }, []);

  const handleAddToCheckout = React.useCallback(
    (reservation: DashboardReservation) => {
      const item = buildCartItem(reservation);
      if (!item) {
        toast("Cannot add reservation without owner information.", "error");
        return;
      }
      add(item);
      toast(`${reservation.pet?.name ?? "Reservation"} added to checkout.`, "success");
    },
    [add, buildCartItem],
  );

  const handleAddSelectedToCheckout = React.useCallback(() => {
    const reservationsToAdd = list.filter((row) => selectedIds.includes(row.id));
    if (!reservationsToAdd.length) {
      toast("Select at least one reservation to add to checkout.", "info");
      return;
    }
    const items = reservationsToAdd
      .map(buildCartItem)
      .filter((item): item is CheckoutCartItem => Boolean(item));
    if (!items.length) {
      toast("Unable to add the selected reservations to checkout.", "error");
      return;
    }
    const ownerIds = new Set(items.map((item) => item.ownerId));
    if (ownerIds.size > 1) {
      toast("Checkout cart can only contain one family at a time.", "error");
      return;
    }
    addMany(items);
    toast(`Added ${items.length} reservation${items.length === 1 ? "" : "s"} to checkout.`, "success");
  }, [list, selectedIds, buildCartItem, addMany]);

  const handleRunPickerClose = React.useCallback(() => {
    setRunPicker(null);
  }, []);

  const handleRunPick = React.useCallback(
    async (runId: string | null) => {
      if (!runPicker) return;
      const reservationsToUpdate = list.filter((row) => runPicker.ids.includes(row.id));
      await Promise.all(
        reservationsToUpdate.map((reservation) =>
          setReservationRunOptimistic(reservation, runId).catch(() => undefined),
        ),
      );
      if (reservationsToUpdate.length === 1) {
        const petName = reservationsToUpdate[0].pet?.name ?? "reservation";
        toast(`Run updated for ${petName}`, "success");
      } else if (reservationsToUpdate.length > 1) {
        toast(`Updated run for ${reservationsToUpdate.length} reservations`, "success");
      }
      clearSelection();
      setRunPicker(null);
    },
    [runPicker, list, setReservationRunOptimistic, clearSelection],
  );

  const handleOpenDrawer = React.useCallback((row: DashboardReservation) => {
    const index = list.findIndex((item) => item.id === row.id);
    if (index >= 0) {
      setFocusIndex(index);
    }
    setDrawerId(row.id);
  }, [list]);

  const handleOpenRunPicker = React.useCallback((row: DashboardReservation) => {
    const index = list.findIndex((item) => item.id === row.id);
    if (index >= 0) {
      setFocusIndex(index);
    }
    setRunPicker({ ids: [row.id], currentRunId: row.run_id ?? null, locationId: row.location_id ?? (locationId || null) });
  }, [list, locationId]);

  const handleCloseDrawer = React.useCallback(() => {
    setDrawerId(null);
  }, []);

  const handleAlertFilter = React.useCallback(
    (kind: AlertKind, payload?: unknown) => {
      if (kind === "unassigned" || kind === "vaccines") {
        setActiveTab("STAYING");
      } else if (kind === "late") {
        setActiveTab("DEPARTING");
      } else if (kind === "waitlist") {
        setActiveTab("REQUESTS");
      }

      if (payload && typeof (payload as { id?: unknown }).id === "string") {
        const targetId = (payload as { id: string }).id;
        const index = list.findIndex((row) => row.id === targetId);
        if (index >= 0) {
          setFocusIndex(index);
          setLastClickedIndex(index);
        }
      }
    },
    [list],
  );

  const handleKeyDown = React.useCallback((event: KeyboardEvent) => {
    const target = event.target as HTMLElement | null;
    if (target) {
      const tag = target.tagName;
      if (target.isContentEditable || tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') {
        return;
      }
    }

    if (!list.length) return;
    const index = Math.max(0, Math.min(focusIndex, list.length - 1));
    const reservation = list[index];

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setFocusIndex((prev) => Math.min(prev + 1, list.length - 1));
      return;
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault();
      setFocusIndex((prev) => Math.max(prev - 1, 0));
      return;
    }

    if (event.key === 'Enter') {
      event.preventDefault();
      handleOpenDrawer(reservation);
      return;
    }

    if (event.key.toLowerCase() === 'c') {
      event.preventDefault();
      void toggleReservationStatus(reservation);
      return;
    }

    if (event.key.toLowerCase() === 'm') {
      event.preventDefault();
      handleOpenRunPicker(reservation);
      return;
    }

    if (event.key.toLowerCase() === 'p') {
      event.preventDefault();
      window.open(`/staff/print/run-card/${reservation.id}`, '_blank', 'noopener');
      return;
    }

    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'a') {
      event.preventDefault();
      selectAllInTab();
      return;
    }

    if (!event.metaKey && !event.ctrlKey && event.key.toLowerCase() === 'a') {
      event.preventDefault();
      setSelection((prev) => {
        const next = { ...prev };
        if (next[reservation.id]) {
          delete next[reservation.id];
        } else {
          next[reservation.id] = true;
        }
        return next;
      });
      setLastClickedIndex(index);
      return;
    }

    if (event.key === 'Escape') {
      if (Object.keys(selection).length) {
        event.preventDefault();
        clearSelection();
      }
      return;
    }
  }, [list, focusIndex, toggleReservationStatus, handleOpenRunPicker, handleOpenDrawer, selectAllInTab, selection, clearSelection]);

  React.useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

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

      <ForecastMini startISO={date} locationId={locationId || undefined} />

      <div className="rounded-xl bg-white p-4 shadow">
        <div className="grid gap-3 md:grid-cols-[repeat(2,minmax(0,1fr))_auto_auto_auto] md:items-end">
          <label className="text-sm font-medium text-slate-700">
            <span className="mb-1 block text-xs uppercase tracking-wide text-slate-500">Date</span>
            <input
              type="date"
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              value={date}
              onChange={(event) => setDate(event.target.value)}
            />
          </label>
          <label className="text-sm font-medium text-slate-700">
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
          <SortControl
            tab={activeTab}
            value={currentSort}
            onChange={(next) => setSortBy((prev) => ({ ...prev, [activeTab]: next }))}
          />
          <button
            type="button"
            className="justify-self-start rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
            onClick={() => handleRefresh()}
          >
            Refresh
          </button>
          <LiveIndicator lastUpdated={lastUpdated} />
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="grid gap-3">
          <BatchBar
            count={selectedIds.length}
            onAddToCheckout={handleAddSelectedToCheckout}
            onCheckIn={handleBatchCheckIn}
            onCheckOut={handleBatchCheckOut}
            onMoveRun={handleBatchMoveRun}
            onPrint={handleBatchPrint}
          />

          <div className="rounded-xl bg-white shadow">
            <div className="flex flex-wrap gap-2 border-b border-slate-200 px-4">
              <TabButton
                label="Arriving"
                count={categories.ARRIVING.length}
                active={activeTab === "ARRIVING"}
                onClick={() => setActiveTab("ARRIVING")}
              />
              <TabButton
                label="Departing"
                count={categories.DEPARTING.length}
                active={activeTab === "DEPARTING"}
                onClick={() => setActiveTab("DEPARTING")}
              />
              <TabButton
                label="Staying"
                count={categories.STAYING.length}
                active={activeTab === "STAYING"}
                onClick={() => setActiveTab("STAYING")}
              />
              <TabButton
                label="Requests"
                count={categories.REQUESTS.length}
                active={activeTab === "REQUESTS"}
                onClick={() => setActiveTab("REQUESTS")}
              />
            </div>
            <div className="p-4">
              {reservationQuery.isLoading ? (
                <div className="text-sm text-slate-500">Loading reservations…</div>
              ) : (
                <>
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
                    <span>{list.length ? `${list.length} reservations` : "No reservations for this view."}</span>
                    {list.length ? (
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          className="rounded border border-slate-200 px-2 py-1 font-medium text-slate-600 hover:bg-slate-100"
                          onClick={selectAllInTab}
                        >
                          Select all
                        </button>
                        {selectedIds.length ? (
                          <button
                            type="button"
                            className="rounded border border-slate-200 px-2 py-1 font-medium text-slate-600 hover:bg-slate-100"
                            onClick={clearSelection}
                          >
                            Clear
                          </button>
                        ) : null}
                      </div>
                    ) : null}
                  </div>

                  {list.length ? (
                    <VirtualList
                      items={list}
                      itemHeight={ROW_HEIGHT}
                      height={LIST_HEIGHT}
                      focusIndex={list.length ? focusIndex : null}
                      render={(reservation, index, isFocused) => (
                        <div key={reservation.id} className="pb-3">
                          <Row
                            row={reservation}
                            vaccineState={reservation.pet?.id ? vaxStates[reservation.pet.id] ?? "unknown" : "unknown"}
                            onRefresh={handleRefresh}
                            checked={!!selection[reservation.id]}
                            onToggleSelection={handleToggleSelection}
                            onOpenDrawer={handleOpenDrawer}
                            onOpenRunPicker={handleOpenRunPicker}
                            onAddToCheckout={handleAddToCheckout}
                            onToggleStatus={toggleReservationStatus}
                            isFocused={isFocused}
                          />
                        </div>
                      )}
                    />
                  ) : (
                    <div className="text-sm text-slate-500">No reservations for this view.</div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>

        <AlertsRail
          dateISO={date}
          locationId={locationId || undefined}
          reservations={data}
          vaccineStates={vaxStates}
          onFilter={handleAlertFilter}
        />
      </div>

      <DrawerReservation
        reservation={drawerReservation}
        onClose={handleCloseDrawer}
        onRefresh={handleRefresh}
      />


      {runPicker && (
        <RunPickerModal
          open
          currentRunId={runPicker.currentRunId ?? null}
          locationId={runPicker.locationId ?? undefined}
          occupancy={occupancy}
          onPick={handleRunPick}
          onClose={handleRunPickerClose}
        />
      )}
    </Page>
  );
}
