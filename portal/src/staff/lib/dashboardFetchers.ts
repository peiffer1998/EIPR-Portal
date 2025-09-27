import api from "../../lib/api";

export type DashboardReservation = {
  id: string;
  reservation_type: string;
  status: string;
  start_at: string;
  end_at: string;
  location_id?: string | null;
  pet: { id?: string; name?: string; species?: string } | null;
  owner: { id?: string; first_name?: string; last_name?: string } | null;
  owner_id?: string | null;
  run_id?: string | null;
  run_name?: string | null;
  feeding_lines?: unknown[] | null;
  medication_lines?: unknown[] | null;
  vaccination_status?: string | null;
};

function mapReservation(raw: any): DashboardReservation {
  const pet = raw?.pet ??
    (raw?.pet_id
      ? { id: raw.pet_id, name: raw.pet_name, species: raw.pet_species }
      : null);
  const owner = raw?.owner ??
    (raw?.owner_id
      ? { id: raw.owner_id, first_name: raw.owner_first_name, last_name: raw.owner_last_name }
      : null);

  return {
    id: String(raw?.id ?? ""),
    reservation_type: raw?.reservation_type ?? raw?.type ?? "BOARDING",
    status: raw?.status ?? "REQUESTED",
    start_at: raw?.start_at ?? raw?.start ?? "",
    end_at: raw?.end_at ?? raw?.end ?? "",
    location_id: raw?.location_id ?? raw?.location?.id ?? null,
    pet,
    owner,
    owner_id: raw?.owner_id ?? raw?.owner?.id ?? null,
    run_id: raw?.run_id ?? raw?.kennel_id ?? raw?.run?.id ?? null,
    run_name: raw?.run?.name ?? raw?.run_name ?? null,
    feeding_lines: raw?.feeding_lines ?? raw?.feeding ?? raw?.feeding_plan ?? null,
    medication_lines: raw?.medication_lines ?? raw?.medications ?? raw?.medication ?? null,
    vaccination_status: raw?.vaccination_status ?? null,
  };
}

export async function listReservationsForDate(dateISO: string, locationId?: string): Promise<DashboardReservation[]> {
  const params: Record<string, unknown> = { date: dateISO, limit: 500 };
  if (locationId) params.location_id = locationId;

  try {
    const { data } = await api.get("/reservations", { params });
    if (!Array.isArray(data)) return [];
    return data.map(mapReservation);
  } catch (error) {
    console.warn("dashboard reservations fetch failed", error);
    return [];
  }
}
