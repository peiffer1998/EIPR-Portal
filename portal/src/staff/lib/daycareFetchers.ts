import api from "../../lib/api";
import type { AxiosResponse } from "axios";

const ok = <T>(promise: Promise<AxiosResponse<T>>): Promise<T> => promise.then((response) => response.data);

type ReservationFallback = {
  id: string;
  pet_id?: string;
  pet_name?: string;
  pet?: { id?: string; name?: string } | null;
  owner?: { id?: string; first_name?: string; last_name?: string } | null;
  owner_id?: string;
  owner_first_name?: string;
  owner_last_name?: string;
  program?: string;
  daycare_program?: string;
  daycare_group?: string | null;
  group?: string | null;
  status?: string;
  check_in_at?: string | null;
  check_out_at?: string | null;
  start_at?: string | null;
  end_at?: string | null;
  location_id?: string;
  late_pickup?: boolean;
  late_flag?: boolean;
  standing?: boolean;
  standing_reservation?: boolean;
  is_standing?: boolean;
};

type DaycareRosterRow = {
  id: string;
  pet: { id?: string; name?: string } | null;
  owner: { id?: string; first_name?: string; last_name?: string } | null;
  program: string;
  group: string | null;
  status: string;
  check_in_at: string | null;
  check_out_at: string | null;
  location_id: string | null;
  late_pickup: boolean;
  standing: boolean;
};

const fallbackProgram = (entry: ReservationFallback): string =>
  entry.program || entry.daycare_program || "Standard";

const normalizeReservation = (entry: ReservationFallback): DaycareRosterRow => ({
  id: entry.id,
  pet: entry.pet || { id: entry.pet_id, name: entry.pet_name },
  owner:
    entry.owner ||
    (entry.owner_id || entry.owner_first_name || entry.owner_last_name
      ? {
          id: entry.owner_id,
          first_name: entry.owner_first_name,
          last_name: entry.owner_last_name,
        }
      : null),
  program: fallbackProgram(entry),
  group: entry.group ?? entry.daycare_group ?? null,
  status: (entry.status || "REQUESTED").toUpperCase(),
  check_in_at: entry.check_in_at || entry.start_at || null,
  check_out_at: entry.check_out_at || entry.end_at || null,
  location_id: entry.location_id ?? null,
  late_pickup: Boolean(entry.late_pickup ?? entry.late_flag),
  standing: Boolean(entry.standing ?? entry.standing_reservation ?? entry.is_standing),
});

export async function getDaycareRoster(
  date: string,
  location_id: string,
  program?: string,
): Promise<DaycareRosterRow[]> {
  if (!date || !location_id) return [];
  try {
    return await ok(
      api.get<DaycareRosterRow[]>("/daycare/roster", {
        params: { date, location_id, program },
      }),
    );
  } catch {
    const reservations = await ok(
      api.get<ReservationFallback[]>("/reservations", {
        params: {
          date,
          location_id,
          reservation_type: "DAYCARE",
          limit: 500,
        },
      }),
    );
    return reservations
      .map(normalizeReservation)
      .filter((row) => (!program ? true : row.program === program));
  }
}

export async function checkIn(reservation_id: string) {
  try {
    return await ok(api.post("/daycare/check-in", { reservation_id }));
  } catch {
    return ok(api.patch(`/reservations/${reservation_id}`, { status: "CHECKED_IN" }));
  }
}

export async function checkOut(reservation_id: string, late?: boolean) {
  try {
    return await ok(api.post("/daycare/check-out", { reservation_id, late: Boolean(late) }));
  } catch {
    return ok(
      api.patch(`/reservations/${reservation_id}`, {
        status: "CHECKED_OUT",
        late_flag: Boolean(late),
      }),
    );
  }
}

export async function assignGroup(reservation_id: string, group: string) {
  try {
    return await ok(api.post("/daycare/assign-group", { reservation_id, group }));
  } catch {
    return ok(api.patch(`/reservations/${reservation_id}`, { group }));
  }
}

export async function logIncident(payload: { reservation_id: string; type: string; note: string }) {
  try {
    return await ok(api.post("/incidents", payload));
  } catch {
    return {
      id: `${payload.reservation_id}-incident-${Date.now()}`,
      ...payload,
      created_at: new Date().toISOString(),
    };
  }
}

export async function listPrograms(location_id: string): Promise<string[]> {
  if (!location_id) return [];
  try {
    return await ok(api.get<string[]>("/daycare/programs", { params: { location_id } }));
  } catch {
    return ["Standard", "Half-Day", "Full-Day"];
  }
}
