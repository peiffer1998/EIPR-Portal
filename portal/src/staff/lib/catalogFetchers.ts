import api from "../../lib/api";

const ok = <T>(p: Promise<{ data: T }>): Promise<T> => p.then((r) => r.data);

export async function listServiceItems(params?: any) {
  try {
    return await ok<any[]>(api.get("/service-items", { params }));
  } catch {
    try {
      return await ok<any[]>(api.get("/services", { params }));
    } catch {
      return [];
    }
  }
}

export async function createServiceItem(payload: {
  name: string;
  duration_min: number;
  price: number;
  active?: boolean;
}) {
  try {
    return await ok<any>(api.post("/service-items", payload));
  } catch {
    return await ok<any>(api.post("/services", payload));
  }
}

export async function updateServiceItem(
  id: string,
  patch: Partial<{
    name: string;
    duration_min: number;
    price: number;
    active: boolean;
  }>,
) {
  try {
    return await ok<any>(api.patch(`/service-items/${id}`, patch));
  } catch {
    return await ok<any>(api.patch(`/services/${id}`, patch));
  }
}

export async function deleteServiceItem(id: string) {
  try {
    await api.delete(`/service-items/${id}`);
    return true;
  } catch {
    try {
      await api.patch(`/services/${id}`, { active: false });
      return true;
    } catch {
      return false;
    }
  }
}

export async function listPackageDefs(params?: any) {
  try {
    return await ok<any[]>(api.get("/packages/defs", { params }));
  } catch {
    return await ok<any[]>(api.get("/packages", { params }));
  }
}

export async function createPackageDef(payload: {
  name: string;
  credits: number;
  credit_unit?: string;
  price: number;
  active?: boolean;
  service_item_id?: string;
  reservation_type?: "boarding" | "daycare" | "grooming";
}) {
  try {
    return await ok<any>(api.post("/packages/defs", payload));
  } catch {
    return await ok<any>(api.post("/packages", payload));
  }
}

export async function updatePackageDef(
  id: string,
  patch: Partial<{
    name: string;
    credits: number;
    credit_unit?: string;
    price: number;
    active: boolean;
    service_item_id?: string;
    reservation_type?: "boarding" | "daycare" | "grooming";
  }>,
) {
  try {
    return await ok<any>(api.patch(`/packages/defs/${id}`, patch));
  } catch {
    return await ok<any>(api.patch(`/packages/${id}`, patch));
  }
}

export async function deletePackageDef(id: string) {
  try {
    await api.delete(`/packages/defs/${id}`);
    return true;
  } catch {
    try {
      await api.patch(`/packages/${id}`, { active: false });
      return true;
    } catch {
      return false;
    }
  }
}
