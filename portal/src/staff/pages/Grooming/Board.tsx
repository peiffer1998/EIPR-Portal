import type { DragEvent } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import GroomingFilters from "../../components/GroomingFilters";
import OwnerPicker from "../../components/OwnerPicker";
import PetPicker from "../../components/PetPicker";
import {
  createAppointment,
  getGroomingBoard,
  getServices,
  getSpecialists,
  rescheduleAppointment,
  setAppointmentStatus,
} from "../../lib/groomingFetchers";

const STEP_MINUTES = 30;
const STEP_MS = STEP_MINUTES * 60 * 1000;

const roundToSlot = (value: number) => Math.floor(value / STEP_MS) * STEP_MS;

const buildSlots = (date: string, startHour = 7, endHour = 19) => {
  const slots: number[] = [];
  const base = new Date(`${date}T00:00:00`);
  for (let hour = startHour; hour < endHour; hour += 1) {
    for (let minute = 0; minute < 60; minute += STEP_MINUTES) {
      const slot = new Date(base);
      slot.setHours(hour, minute, 0, 0);
      slots.push(slot.getTime());
    }
  }
  return slots;
};

const formatTime = (value: number) => {
  const date = new Date(value);
  const hours24 = date.getHours();
  const hours12 = hours24 % 12 || 12;
  const minutes = `${date.getMinutes()}`.padStart(2, "0");
  const suffix = hours24 < 12 ? "AM" : "PM";
  return `${hours12}:${minutes} ${suffix}`;
};

type Filters = {
  date: string;
  location_id: string;
  service_id?: string;
  q?: string;
};

type Appointment = {
  id: string;
  specialist_id: string;
  specialist_name?: string;
  start_at: string;
  end_at?: string | null;
  duration_min?: number | null;
  pet?: any;
  owner?: any;
  status?: string;
  service_name?: string;
  service_id?: string;
};

export default function GroomingBoard() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<Filters>({
    date: new Date().toISOString().slice(0, 10),
    location_id: localStorage.getItem("defaultLocationId") || "",
  });
  const [dialogOpen, setDialogOpen] = useState(false);
  const [ownerId, setOwnerId] = useState<string | undefined>();
  const [petId, setPetId] = useState<string | undefined>();
  const newApptFormRef = useRef<HTMLFormElement>(null);
  const dragPayload = useRef<{ id: string } | null>(null);

  const specialistsQuery = useQuery({
    queryKey: ["grooming-specialists", filters.location_id],
    queryFn: () => getSpecialists(filters.location_id),
    enabled: Boolean(filters.location_id),
  });

  const servicesQuery = useQuery({
    queryKey: ["grooming-services", filters.location_id],
    queryFn: () => getServices(filters.location_id),
    enabled: Boolean(filters.location_id),
  });

  const boardQuery = useQuery({
    queryKey: ["grooming-board", filters.date, filters.location_id, filters.service_id],
    queryFn: () => getGroomingBoard(filters.date, filters.location_id, filters.service_id),
    enabled: Boolean(filters.date && filters.location_id),
  });

  const appointments = useMemo<Appointment[]>(() => {
    const data = Array.isArray(boardQuery.data) ? (boardQuery.data as Appointment[]) : [];
    if (!filters.q) return data;
    const search = filters.q.toLowerCase();
    return data.filter((item) => {
      const pet = (item.pet?.name || "").toLowerCase();
      const owner = `${item.owner?.first_name || ""} ${item.owner?.last_name || ""}`.toLowerCase();
      return pet.includes(search) || owner.includes(search);
    });
  }, [boardQuery.data, filters.q]);

  const columns = useMemo(() => {
    const map = new Map<string, { id: string; name: string }>();
    (Array.isArray(specialistsQuery.data) ? specialistsQuery.data : []).forEach((specialist: any) => {
      const id = specialist.id || specialist.user_id || specialist.specialist_id;
      if (!id) return;
      map.set(id, { id, name: specialist.name || specialist.display_name || id });
    });
    appointments.forEach((appt) => {
      if (!map.has(appt.specialist_id)) {
        map.set(appt.specialist_id, {
          id: appt.specialist_id,
          name: appt.specialist_name || appt.specialist_id || "Unassigned",
        });
      }
    });
    if (!map.size) {
      map.set("unassigned", { id: "unassigned", name: "Unassigned" });
    }
    return Array.from(map.values());
  }, [appointments, specialistsQuery.data]);

  const grouped = useMemo(() => {
    const seeds: Record<string, Record<number, Appointment>> = {};
    columns.forEach((column) => {
      seeds[column.id] = {};
    });
    appointments.forEach((appt) => {
      const columnId = seeds[appt.specialist_id] ? appt.specialist_id : columns[0]?.id;
      if (!columnId) return;
      const ms = roundToSlot(new Date(appt.start_at).getTime());
      seeds[columnId][ms] = appt;
    });
    return seeds;
  }, [appointments, columns]);

  const slots = useMemo(() => buildSlots(filters.date), [filters.date]);

  const reschedule = useMutation({
    mutationFn: ({ id, start_at, specialist_id }: { id: string; start_at: string; specialist_id: string }) =>
      rescheduleAppointment(id, start_at, specialist_id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["grooming-board"] }),
  });

  const setStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => setAppointmentStatus(id, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["grooming-board"] }),
  });

  const create = useMutation({
    mutationFn: async () => {
      const form = newApptFormRef.current;
      if (!form) return;
      const fd = new FormData(form);
      const startInput = fd.get("start_at");
      if (!startInput) throw new Error("Start time required");
      const rawMs = new Date(String(startInput)).getTime();
      const snapped = roundToSlot(rawMs);
      const payload = {
        owner_id: ownerId || undefined,
        pet_id: petId || undefined,
        specialist_id: fd.get("specialist_id") || undefined,
        service_id: fd.get("service_id") || undefined,
        addon_ids: String(fd.get("addon_ids") || "")
          .split(",")
          .map((value) => value.trim())
          .filter(Boolean),
        start_at: new Date(snapped).toISOString(),
        notes: fd.get("notes") || undefined,
        reservation_id: fd.get("reservation_id") || undefined,
      };
      return createAppointment(payload);
    },
    onSuccess: () => {
      setDialogOpen(false);
      queryClient.invalidateQueries({ queryKey: ["grooming-board"] });
    },
  });

  useEffect(() => {
    if (!dialogOpen) {
      setOwnerId(undefined);
      setPetId(undefined);
      newApptFormRef.current?.reset();
    }
  }, [dialogOpen]);

  const handleDrop = (specialistId: string, slotMs: number) => async (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    const id = dragPayload.current?.id || event.dataTransfer.getData("text/plain");
    dragPayload.current = null;
    if (!id) return;
    await reschedule.mutateAsync({ id, start_at: new Date(slotMs).toISOString(), specialist_id: specialistId });
  };

  const handleDragStart = (id: string) => (event: DragEvent<HTMLDivElement>) => {
    dragPayload.current = { id };
    event.dataTransfer.setData("text/plain", id);
    event.dataTransfer.effectAllowed = "move";
  };

  return (
    <div className="grid gap-4">
      <GroomingFilters onChange={setFilters} />

      <div className="flex items-center justify-between">
        <div className="text-sm text-slate-600">
          {Array.isArray(appointments) ? appointments.length : 0} appointments
        </div>
        <button
          type="button"
          className="rounded bg-slate-900 px-3 py-2 text-white shadow-sm"
          onClick={() => setDialogOpen(true)}
        >
          New Appointment
        </button>
      </div>

      <div className="bg-white rounded-xl shadow overflow-auto">
        <div className="min-w-[960px]">
          <div className="grid sticky top-0 z-10 bg-white" style={{ gridTemplateColumns: `160px repeat(${columns.length}, minmax(220px, 1fr))` }}>
            <div className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Time</div>
            {columns.map((column) => (
              <div key={column.id} className="px-3 py-2 text-sm font-semibold border-l border-slate-200">
                {column.name}
              </div>
            ))}
          </div>

          {slots.map((slot) => (
            <div
              key={slot}
              className="grid border-t border-slate-200"
              style={{ gridTemplateColumns: `160px repeat(${columns.length}, minmax(220px, 1fr))` }}
            >
              <div className="px-3 py-2 text-xs font-medium text-slate-500 bg-slate-50">{formatTime(slot)}</div>
              {columns.map((column, index) => {
                const appointment = grouped[column.id]?.[slot];
                return (
                  <div
                    key={`${slot}-${column.id}`}
                    className={`px-2 py-1 border-l border-slate-200 min-h-[52px] ${index % 2 === 1 ? "bg-slate-50/40" : "bg-white"}`}
                    onDragOver={(event) => {
                      event.preventDefault();
                      event.dataTransfer.dropEffect = "move";
                    }}
                    onDrop={handleDrop(column.id, slot)}
                  >
                    {!appointment ? null : (
                      <div
                        role="button"
                        tabIndex={0}
                        draggable
                        onDragStart={handleDragStart(appointment.id)}
                        className="rounded-lg border border-orange-200 bg-orange-50 px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-400"
                      >
                        <div className="font-medium leading-tight">
                          {appointment.pet?.name || appointment.id}
                          {appointment.service_name ? (
                            <span className="ml-1 text-xs text-slate-500">({appointment.service_name})</span>
                          ) : null}
                        </div>
                        <div className="text-xs text-slate-600">
                          {formatTime(new Date(appointment.start_at).getTime())} • {appointment.status || "BOOKED"}
                        </div>
                        <div className="mt-2 flex flex-wrap gap-1">
                          <button
                            type="button"
                            className="text-[11px] rounded bg-green-600 px-2 py-1 text-white"
                            onClick={() => setStatus.mutate({ id: appointment.id, status: "ARRIVED" })}
                          >
                            Arrived
                          </button>
                          <button
                            type="button"
                            className="text-[11px] rounded bg-blue-600 px-2 py-1 text-white"
                            onClick={() => setStatus.mutate({ id: appointment.id, status: "IN_PROGRESS" })}
                          >
                            In-Progress
                          </button>
                          <button
                            type="button"
                            className="text-[11px] rounded bg-purple-700 px-2 py-1 text-white"
                            onClick={() => setStatus.mutate({ id: appointment.id, status: "COMPLETE" })}
                          >
                            Complete
                          </button>
                          <button
                            type="button"
                            className="text-[11px] rounded bg-slate-700 px-2 py-1 text-white"
                            onClick={() => setStatus.mutate({ id: appointment.id, status: "PICKED_UP" })}
                          >
                            Picked-Up
                          </button>
                          <a
                            className="text-[11px] rounded border border-slate-300 px-2 py-1 text-slate-600 hover:bg-slate-100"
                            href={`/staff/print/groom-ticket/${appointment.id}`}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Ticket
                          </a>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {dialogOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <form
            ref={newApptFormRef}
            className="w-full max-w-2xl rounded-xl bg-white p-5 shadow-xl"
            onSubmit={(event) => event.preventDefault()}
          >
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-lg font-semibold">New Grooming Appointment</h2>
                <p className="text-sm text-slate-600">Search for the owner and pet, then choose timing and service.</p>
              </div>
              <button type="button" className="rounded border px-3 py-1" onClick={() => setDialogOpen(false)}>
                Close
              </button>
            </div>

            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <OwnerPicker onPick={setOwnerId} />
                <p className="text-xs text-slate-500">Selected owner: {ownerId || "None"}</p>
              </div>
              <div className="space-y-2">
                <PetPicker ownerId={ownerId} onPick={setPetId} />
                <p className="text-xs text-slate-500">Selected pet: {petId || "None"}</p>
              </div>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <label className="text-sm grid gap-1">
                <span className="text-slate-600">Specialist</span>
                <select name="specialist_id" className="border rounded px-3 py-2">
                  <option value="">Unassigned</option>
                  {(Array.isArray(specialistsQuery.data) ? specialistsQuery.data : []).map((specialist: any) => {
                    const id = specialist.id || specialist.user_id || specialist.specialist_id;
                    return (
                      <option key={id} value={id}>
                        {specialist.name || specialist.display_name || id}
                      </option>
                    );
                  })}
                </select>
              </label>

              <label className="text-sm grid gap-1">
                <span className="text-slate-600">Service</span>
                <select name="service_id" className="border rounded px-3 py-2">
                  <option value="">Select service</option>
                  {(Array.isArray(servicesQuery.data) ? servicesQuery.data : []).map((service: any) => (
                    <option key={service.id} value={service.id}>
                      {service.name || service.id}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <label className="text-sm grid gap-1">
                <span className="text-slate-600">Start time</span>
                <input
                  name="start_at"
                  type="datetime-local"
                  className="border rounded px-3 py-2"
                  defaultValue={`${filters.date}T09:00`}
                />
              </label>

              <label className="text-sm grid gap-1">
                <span className="text-slate-600">Add-on IDs</span>
                <input
                  name="addon_ids"
                  className="border rounded px-3 py-2"
                  placeholder="comma separated UUIDs"
                />
              </label>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <label className="text-sm grid gap-1">
                <span className="text-slate-600">Reservation ID (optional)</span>
                <input name="reservation_id" className="border rounded px-3 py-2" />
              </label>

              <label className="text-sm grid gap-1">
                <span className="text-slate-600">Notes</span>
                <textarea name="notes" rows={3} className="border rounded px-3 py-2" />
              </label>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button type="button" className="rounded border px-4 py-2" onClick={() => setDialogOpen(false)}>
                Cancel
              </button>
              <button
                type="button"
                className="rounded bg-slate-900 px-4 py-2 text-white"
                onClick={() => create.mutate()}
                disabled={create.isPending}
              >
                {create.isPending ? "Creating…" : "Create Appointment"}
              </button>
            </div>
          </form>
        </div>
      ) : null}
    </div>
  );
}
