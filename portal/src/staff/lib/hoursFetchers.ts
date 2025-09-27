import api from "../../lib/api";

const ok = <T>(promise: Promise<{ data: T }>): Promise<T> => promise.then((response) => response.data);

export type DayRow = {
  weekday: number;
  is_closed: boolean;
  open?: string | null;
  close?: string | null;
};

export type HoursPayload = {
  days: DayRow[];
};

export async function getLocationHours(locationId: string): Promise<HoursPayload> {
  try {
    return await ok<HoursPayload>(api.get(`/locations/${locationId}/hours`));
  } catch {
    const days = Array.from({ length: 7 }, (_, index) => ({
      weekday: index,
      is_closed: true,
      open: null,
      close: null,
    }));
    return { days };
  }
}

export async function setLocationHours(locationId: string, days: DayRow[]): Promise<void> {
  try {
    await api.put(`/locations/${locationId}/hours`, { days });
  } catch {
    await Promise.all(
      days.map(async (day) => {
        try {
          await api.patch(`/locations/${locationId}/hours/${day.weekday}`, day);
        } catch {
          /* ignore */
        }
      }),
    );
  }
}

export type Closure = {
  id?: string;
  start_date: string;
  end_date: string;
  reason?: string;
};

export async function listClosures(locationId: string): Promise<Closure[]> {
  try {
    return await ok<Closure[]>(api.get(`/locations/${locationId}/closures`));
  } catch {
    return [];
  }
}

export async function createClosure(locationId: string, payload: Closure): Promise<void> {
  try {
    await api.post(`/locations/${locationId}/closures`, payload);
  } catch {
    await api.post(`/closures`, { location_id: locationId, ...payload });
  }
}

export async function deleteClosure(locationId: string, closureId: string): Promise<void> {
  try {
    await api.delete(`/locations/${locationId}/closures/${closureId}`);
  } catch {
    await api.delete(`/closures/${closureId}`);
  }
}
