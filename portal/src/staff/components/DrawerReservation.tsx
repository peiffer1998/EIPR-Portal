import React from "react";
import type { DashboardReservation } from "../lib/dashboardFetchers";
import { checkIn, checkOut, moveRun, listRuns } from "../lib/reservationOps";
import { quickEmail, quickSms } from "../lib/dashboardActions";

export type DrawerReservationProps = {
  reservation: DashboardReservation | null;
  onClose: () => void;
  onRefresh: () => Promise<void> | void;
};

type RunOption = { id: string; name?: string | null };

export default function DrawerReservation({ reservation, onClose, onRefresh }: DrawerReservationProps) {
  const [runs, setRuns] = React.useState<RunOption[]>([]);
  const [runChoice, setRunChoice] = React.useState<string>("");
  const [sending, setSending] = React.useState<"sms" | "email" | null>(null);
  const [moving, setMoving] = React.useState(false);
  const [toggling, setToggling] = React.useState(false);

  React.useEffect(() => {
    const currentRun = reservation?.run_id ?? "";
    setRunChoice(currentRun || "");
  }, [reservation?.run_id, reservation?.id]);

  React.useEffect(() => {
    let cancelled = false;
    async function loadRuns() {
      if (!reservation?.location_id) {
        setRuns([]);
        return;
      }
      try {
        const data = await listRuns(reservation.location_id);
        if (!cancelled) setRuns(Array.isArray(data) ? data : []);
      } catch (error) {
        console.warn("drawer run list failed", error);
        if (!cancelled) setRuns([]);
      }
    }
    loadRuns();
    return () => {
      cancelled = true;
    };
  }, [reservation?.location_id]);

  if (!reservation) return null;

  const petName = reservation.pet?.name ?? reservation.pet?.id ?? "Pet";
  const ownerName = `${reservation.owner?.first_name ?? ""} ${reservation.owner?.last_name ?? ""}`.trim();

  async function handleMove() {
    if (!reservation) return;
    setMoving(true);
    try {
      const target = runChoice || null;
      await moveRun(reservation.id, target);
      await onRefresh();
    } finally {
      setMoving(false);
    }
  }

  async function handleToggleStatus() {
    if (!reservation) return;
    setToggling(true);
    try {
      if (reservation.status === "CHECKED_IN") {
        await checkOut(reservation.id);
      } else {
        await checkIn(reservation.id, reservation.run_id ?? undefined);
      }
      await onRefresh();
    } finally {
      setToggling(false);
    }
  }

  async function handleQuickSend(kind: "sms" | "email") {
    if (!reservation) return;
    const ownerId = String(reservation.owner?.id ?? reservation.owner_id ?? "");
    if (!ownerId) return;

    const variables = {
      pet_name: reservation.pet?.name ?? "",
      reservation_id: reservation.id,
    } satisfies Record<string, unknown>;

    setSending(kind);
    try {
      const template = "notify.reservation.checkin";
      if (kind === "sms") {
        await quickSms(ownerId, template, variables);
      } else {
        await quickEmail(ownerId, template, variables);
      }
      window.alert("Message sent");
    } finally {
      setSending(null);
    }
  }

  return (
    <div className="fixed inset-0 z-40">
      <div
        className="absolute inset-0 bg-slate-900/40"
        role="presentation"
        onClick={onClose}
      />
      <aside className="absolute right-0 top-0 flex h-full w-full max-w-md flex-col gap-4 overflow-y-auto bg-white p-5 shadow-2xl">
        <header className="flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-500">Reservation</p>
            <h2 className="text-lg font-semibold text-slate-900">{petName}</h2>
            {ownerName ? <p className="text-sm text-slate-600">{ownerName}</p> : null}
          </div>
          <button
            type="button"
            className="rounded border border-slate-200 px-3 py-1 text-sm font-medium text-slate-600 transition hover:bg-slate-100"
            onClick={onClose}
          >
            Close
          </button>
        </header>

        <section className="grid gap-2 text-sm text-slate-600">
          <div className="font-medium text-slate-800">Status: {reservation.status}</div>
          <div>Type: {reservation.reservation_type}</div>
          <div>Run: {reservation.run_name ?? reservation.run_id ?? "Unassigned"}</div>
          <div>Start: {reservation.start_at}</div>
          <div>End: {reservation.end_at}</div>
        </section>

        <section className="grid gap-2">
          <label className="text-sm font-medium text-slate-700">
            <span className="mb-1 block text-xs uppercase tracking-wide text-slate-500">Assign to run</span>
            <select
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              value={runChoice}
              onChange={(event) => setRunChoice(event.target.value)}
            >
              <option value="">Unassigned</option>
              {runs.map((run) => (
                <option key={run.id} value={run.id}>
                  {run.name ?? run.id}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="rounded bg-slate-900 px-3 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            onClick={handleMove}
            disabled={moving}
          >
            {moving ? "Moving…" : "Move to Run"}
          </button>
        </section>

        <section className="grid gap-2">
          <button
            type="button"
            className="rounded bg-orange-500 px-3 py-2 text-sm font-semibold text-white transition hover:bg-orange-600 disabled:cursor-not-allowed disabled:opacity-60"
            onClick={handleToggleStatus}
            disabled={toggling}
          >
            {reservation.status === "CHECKED_IN" ? (toggling ? "Checking out…" : "Check-Out") : toggling ? "Checking in…" : "Check-In"}
          </button>
          <a
            href={`/staff/print/run-card/${reservation.id}`}
            target="_blank"
            rel="noreferrer"
            className="rounded border border-slate-200 px-3 py-2 text-center text-sm font-medium text-slate-700 transition hover:bg-slate-100"
          >
            Print Run Card
          </a>
        </section>

        <section className="grid gap-2">
          <p className="text-sm font-semibold text-slate-700">Quick message</p>
          <div className="flex gap-2">
            <button
              type="button"
              className="flex-1 rounded border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
              onClick={() => handleQuickSend("sms")}
              disabled={sending === "sms"}
            >
              {sending === "sms" ? "Sending…" : "Send SMS"}
            </button>
            <button
              type="button"
              className="flex-1 rounded border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
              onClick={() => handleQuickSend("email")}
              disabled={sending === "email"}
            >
              {sending === "email" ? "Sending…" : "Send Email"}
            </button>
          </div>
          <p className="text-xs text-slate-500">
            Uses your existing notification templates (defaults to <code>notify.reservation.checkin</code>).
          </p>
        </section>
      </aside>
    </div>
  );
}
