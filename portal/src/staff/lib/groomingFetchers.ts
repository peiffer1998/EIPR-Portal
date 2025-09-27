import api from "../../lib/api";

const ok = <T>(promise: Promise<{ data: T }>): Promise<T> => promise.then((response) => response.data);

type Specialist = {
  id?: string;
  user_id?: string;
  specialist_id?: string;
  name?: string;
  display_name?: string;
};

type Appointment = {
  id: string;
  specialist_id: string;
  start_at: string;
  end_at?: string | null;
  duration_min?: number | null;
  pet?: any;
  owner?: any;
  service?: any;
  status?: string;
  service_id?: string;
  service_name?: string;
  specialist?: any;
  location_id?: string;
  addon_names?: string[];
};

export async function getSpecialists(locationId: string) {
  try {
    return await ok<Specialist[]>(api.get("/grooming/specialists", { params: { location_id: locationId } }));
  } catch {
    try {
      return await ok<Specialist[]>(api.get("/specialists", { params: { location_id: locationId } }));
    } catch {
      return [] as Specialist[];
    }
  }
}

export async function getServices(locationId: string) {
  try {
    return await ok<any[]>(api.get("/grooming/services", { params: { location_id: locationId } }));
  } catch {
    return [] as any[];
  }
}

export async function getGroomingBoard(date: string, locationId: string, serviceId?: string) {
  try {
    return await ok<Appointment[]>(
      api.get("/grooming/appointments/board", { params: { date, location_id: locationId, service_id: serviceId } }),
    );
  } catch {
    const fallback = await ok<any[]>(
      api.get("/grooming/appointments", { params: { date, location_id: locationId, service_id: serviceId, limit: 500 } }),
    );
    return fallback.map((item) => ({
      id: item.id,
      specialist_id: item.specialist_id,
      specialist_name: item.specialist?.name ?? item.specialist_name ?? item.specialist_id,
      start_at: item.start_at,
      end_at: item.end_at,
      duration_min: item.duration_min ?? 60,
      pet: item.pet ?? { id: item.pet_id, name: item.pet_name },
      owner: item.owner ?? {
        id: item.owner_id,
        first_name: item.owner_first_name,
        last_name: item.owner_last_name,
      },
      status: (item.status || "BOOKED").toUpperCase(),
      service_id: item.service_id,
      service_name: item.service?.name ?? item.service_name ?? "",
      location_id: item.location_id,
      addon_names: item.addon_names ?? [],
      service: item.service,
    }));
  }
}

export async function createAppointment(payload: Record<string, unknown>) {
  return ok(api.post("/grooming/appointments", payload));
}

export async function rescheduleAppointment(id: string, startAt: string, specialistId?: string) {
  try {
    return await ok(api.post(`/grooming/appointments/${id}/reschedule`, { start_at: startAt, specialist_id: specialistId }));
  } catch {
    return ok(api.patch(`/grooming/appointments/${id}`, { start_at: startAt, specialist_id: specialistId }));
  }
}

export async function setAppointmentStatus(id: string, status: string) {
  try {
    return await ok(api.post(`/grooming/appointments/${id}/status`, { status }));
  } catch {
    return ok(api.patch(`/grooming/appointments/${id}`, { status }));
  }
}

export async function getAppointment(id: string) {
  try {
    return await ok<Appointment>(api.get(`/grooming/appointments/${id}`));
  } catch {
    return ok<Appointment>(api.get(`/appointments/${id}`));
  }
}
