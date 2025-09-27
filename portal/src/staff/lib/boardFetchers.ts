import api from "../../lib/api";

const ok = <T>(promise: Promise<{ data: T }>): Promise<T> => promise.then((response) => response.data);

type ReservationLike = {
  id: string;
  pet_id?: string;
  pet_name?: string;
  pet?: { id: string; name?: string };
  owner?: { id: string; first_name?: string; last_name?: string };
  run_id?: string;
  run_name?: string;
  run?: { id: string; name?: string };
  feeding?: any[];
  feeding_lines?: any[];
  medications?: any[];
  medication_lines?: any[];
  belongings?: any[];
};

type Filters = {
  date: string;
  location_id: string;
  reservation_type?: string;
};

type Nullable<T> = T | null | undefined;

const normalizeRun = (run: Nullable<{ id?: string; name?: string }>, fallbackId?: string, fallbackName?: string) => ({
  id: run?.id ?? fallbackId ?? "",
  name: run?.name ?? fallbackName ?? "",
});

const normalizePet = (pet: Nullable<{ id?: string; name?: string }>, fallbackId?: string, fallbackName?: string) => ({
  id: pet?.id ?? fallbackId ?? "",
  name: pet?.name ?? fallbackName ?? "",
});

const uppercase = (value: Nullable<string>, fallback = "PENDING") => (value ? value.toUpperCase() : fallback);

async function fetchReservations(filters: Filters) {
  try {
    return await ok<ReservationLike[]>(
      api.get("/reservations", {
        params: {
          date: filters.date,
          location_id: filters.location_id,
          reservation_type: filters.reservation_type ?? "BOARDING",
          limit: 500,
        },
      }),
    );
  } catch {
    return [] as ReservationLike[];
  }
}

export async function getFeedingBoard(date: string, locationId: string) {
  if (!date || !locationId) return [] as any[];

  try {
    return await ok<any[]>(
      api.get("/boards/feeding", {
        params: { date, location_id: locationId },
      }),
    );
  } catch {
    const reservations = await fetchReservations({ date, location_id: locationId });
    const rows: any[] = [];

    reservations.forEach((reservation) => {
      const lines = (reservation.feeding_lines || reservation.feeding || []) as any[];
      lines.forEach((line, index) => {
        rows.push({
          id: line.id || `${reservation.id}:feeding:${index}`,
          reservation_id: reservation.id,
          pet: normalizePet(reservation.pet, reservation.pet_id, reservation.pet_name),
          run: normalizeRun(reservation.run, reservation.run_id, reservation.run_name),
          time: line.time || line.when || null,
          amount: line.amount || "",
          food: line.food || "",
          notes: line.notes || "",
          status: uppercase(line.status),
        });
      });
    });

    return rows;
  }
}

export async function updateFeedingItem(itemId: string, patch: Record<string, unknown>) {
  try {
    return await ok(api.patch(`/feeding/${itemId}`, patch));
  } catch {
    const [reservationId] = String(itemId).split(":");
    return ok(api.post(`/reservations/${reservationId}/feeding/update`, patch));
  }
}

export async function getMedsBoard(date: string, locationId: string) {
  if (!date || !locationId) return [] as any[];

  try {
    return await ok<any[]>(
      api.get("/boards/meds", {
        params: { date, location_id: locationId },
      }),
    );
  } catch {
    const reservations = await fetchReservations({ date, location_id: locationId });
    const rows: any[] = [];

    reservations.forEach((reservation) => {
      const lines = (reservation.medication_lines || reservation.medications || []) as any[];
      lines.forEach((line, index) => {
        rows.push({
          id: line.id || `${reservation.id}:med:${index}`,
          reservation_id: reservation.id,
          pet: normalizePet(reservation.pet, reservation.pet_id, reservation.pet_name),
          run: normalizeRun(reservation.run, reservation.run_id, reservation.run_name),
          time: line.time || line.when || null,
          med: line.med || line.name || "",
          dose: line.dose || "",
          notes: line.notes || "",
          status: uppercase(line.status),
        });
      });
    });

    return rows;
  }
}

export async function updateMedsItem(itemId: string, patch: Record<string, unknown>) {
  try {
    return await ok(api.patch(`/meds/${itemId}`, patch));
  } catch {
    const [reservationId] = String(itemId).split(":");
    return ok(api.post(`/reservations/${reservationId}/meds/update`, patch));
  }
}

export async function getBelongings(date: string, locationId: string) {
  if (!date || !locationId) return [] as any[];

  try {
    return await ok<any[]>(
      api.get("/belongings", {
        params: { date, location_id: locationId },
      }),
    );
  } catch {
    const reservations = await fetchReservations({ date, location_id: locationId });
    const rows: any[] = [];

    reservations.forEach((reservation) => {
      const items = (reservation.belongings || []) as any[];
      items.forEach((item, index) => {
        rows.push({
          id: item.id || `${reservation.id}:belonging:${index}`,
          reservation_id: reservation.id,
          pet: normalizePet(reservation.pet, reservation.pet_id, reservation.pet_name),
          run: normalizeRun(reservation.run, reservation.run_id, reservation.run_name),
          name: item.name || "",
          note: item.note || "",
          returned: Boolean(item.returned),
        });
      });
    });

    return rows;
  }
}

export async function addBelonging(reservationId: string, payload: { name: string; note?: string }) {
  try {
    return await ok(api.post("/belongings", { reservation_id: reservationId, ...payload }));
  } catch {
    try {
      return await ok(api.post(`/reservations/${reservationId}/belongings`, payload));
    } catch {
      return { reservation_id: reservationId, ...payload };
    }
  }
}

export async function setBelongingReturned(itemId: string, returned: boolean) {
  try {
    return await ok(api.patch(`/belongings/${itemId}`, { returned }));
  } catch {
    return { id: itemId, returned };
  }
}
