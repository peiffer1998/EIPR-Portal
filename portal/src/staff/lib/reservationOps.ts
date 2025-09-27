import api from "../../lib/api";

const ok = <T>(promise: Promise<{ data: T }>): Promise<T> => promise.then((response) => response.data);

export const getReservation = (id: string) => ok<any>(api.get(`/reservations/${id}`));
export const updateReservation = (id: string, payload: any) => ok<any>(api.patch(`/reservations/${id}`, payload));
export const cancelReservation = (id: string, reason?: string) =>
  ok<any>(
    api
      .post(`/reservations/${id}/cancel`, { reason })
      .catch(() => api.patch(`/reservations/${id}`, { status: "CANCELED", cancel_reason: reason }).then((res) => res)),
  );
export const noShowReservation = (id: string) =>
  ok<any>(
    api
      .post(`/reservations/${id}/no-show`)
      .catch(() => api.patch(`/reservations/${id}`, { status: "NO_SHOW" }).then((res) => res)),
  );
export const checkIn = (id: string, runId?: string) =>
  ok<any>(
    api
      .post(`/reservations/${id}/check-in`, { run_id: runId })
      .catch(() => api.patch(`/reservations/${id}`, { status: "CHECKED_IN", run_id: runId ?? null }).then((res) => res)),
  );
export const checkOut = (id: string) =>
  ok<any>(
    api
      .post(`/reservations/${id}/check-out`)
      .catch(() => api.patch(`/reservations/${id}`, { status: "CHECKED_OUT" }).then((res) => res)),
  );
export const moveRun = (id: string, runId: string | null | undefined) =>
  ok<any>(
    api
      .post(`/reservations/${id}/move-run`, { run_id: runId ?? null })
      .catch(() => api.patch(`/reservations/${id}`, { run_id: runId ?? null }).then((res) => res)),
  );
export const listRuns = (locationId?: string) => {
  const params: Record<string, unknown> = { limit: 200 };
  if (locationId) params.location_id = locationId;
  return ok<any[]>(api.get(`/runs`, { params }));
};
export const capacityWindow = (
  locationId: string,
  start: string,
  end: string,
  reservationType?: string,
) =>
  ok<any[]>(
    api.get(`/reports/occupancy`, {
      params: { start_date: start, end_date: end, location_id: locationId, reservation_type: reservationType },
    }),
  );
