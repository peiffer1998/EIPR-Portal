import api from "../../lib/api";

const ok = <T>(promise: Promise<{ data: T }>): Promise<T> => promise.then((response) => response.data);

export async function listLocations() {
  try {
    return await ok<any[]>(api.get("/locations", { params: { limit: 100 } }));
  } catch {
    // If the API is not yet implemented, fall back to an empty list so the UI still renders.
    return [] as any[];
  }
}
