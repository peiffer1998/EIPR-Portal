import api from "../../lib/api";

export type DailyAvailability = {
  date: string;
  capacity: number | null;
  booked: number;
  available: number | null;
};

function addDays(baseIso: string, offset: number) {
  const date = new Date(`${baseIso}T00:00:00`);
  date.setDate(date.getDate() + offset);
  return date.toISOString().slice(0, 10);
}

async function safeGet<T>(path: string, params: Record<string, unknown>): Promise<T | null> {
  try {
    const { data } = await api.get<T>(path, { params });
    return data;
  } catch (error) {
    console.warn("forecast fetch failed", path, error);
    return null;
  }
}

export async function getBoardingAvailability(
  locationId: string | undefined,
  startIso: string,
  days: number,
): Promise<DailyAvailability[]> {
  const params: Record<string, unknown> = {
    reservation_type: "BOARDING",
    start_date: startIso,
    end_date: addDays(startIso, days - 1),
  };
  if (locationId) params.location_id = locationId;

  const primary = await safeGet<any>("/reservations/availability/daily", params);
  if (primary) {
    const rows = Array.isArray(primary?.days) ? primary.days : Array.isArray(primary) ? primary : [];
    if (Array.isArray(rows) && rows.length) {
      return rows.map((entry: any) => {
        const capacity = entry?.capacity ?? null;
        const booked = Number(entry?.booked ?? 0);
        return {
          date: String(entry?.date ?? '').slice(0, 10),
          capacity: capacity === undefined ? null : Number(capacity),
          booked,
          available:
            entry?.available != null
              ? Number(entry.available)
              : capacity != null
                ? Number(capacity) - booked
                : null,
        };
      });
    }
  }

  const fallback: DailyAvailability[] = [];
  for (let i = 0; i < days; i += 1) {
    const day = addDays(startIso, i);
    const fallbackParams: Record<string, unknown> = {
      date: day,
      reservation_type: "BOARDING",
      limit: 500,
    };
    if (locationId) fallbackParams.location_id = locationId;

    const reservations = await safeGet<any[]>("/reservations", fallbackParams);
    const booked = Array.isArray(reservations)
      ? reservations.filter((reservation) => reservation?.status !== 'CANCELED').length
      : 0;
    fallback.push({ date: day, capacity: null, booked, available: null });
  }
  return fallback;
}

export async function getDaycareCounts(
  locationId: string | undefined,
  startIso: string,
  days: number,
): Promise<{ date: string; count: number }[]> {
  const results: { date: string; count: number }[] = [];
  for (let i = 0; i < days; i += 1) {
    const day = addDays(startIso, i);
    const params: Record<string, unknown> = {
      date: day,
      reservation_type: "DAYCARE",
      limit: 500,
    };
    if (locationId) params.location_id = locationId;
    const reservations = await safeGet<any[]>("/reservations", params);
    const count = Array.isArray(reservations)
      ? reservations.filter((reservation) => reservation?.status !== 'CANCELED').length
      : 0;
    results.push({ date: day, count });
  }
  return results;
}

export async function getGroomingCounts(
  locationId: string | undefined,
  startIso: string,
  days: number,
): Promise<{ date: string; count: number }[]> {
  const results: { date: string; count: number }[] = [];
  for (let i = 0; i < days; i += 1) {
    const day = addDays(startIso, i);
    const params: Record<string, unknown> = {
      date: day,
      limit: 500,
    };
    if (locationId) params.location_id = locationId;
    const appointments = await safeGet<any[]>("/grooming/appointments", params);
    const count = Array.isArray(appointments) ? appointments.length : 0;
    results.push({ date: day, count });
  }
  return results;
}
