import api from "../../lib/api";

export type Role = "SUPERADMIN" | "ADMIN" | "MANAGER" | "STAFF" | "PET_PARENT";
export type Me = {
  id: string;
  email: string;
  role: Role;
  account_id?: string;
  first_name?: string;
  last_name?: string;
};

export async function loginWithPassword(email: string, password: string) {
  const body = new URLSearchParams({ username: email, password });
  const { data } = await api.post<{ access_token: string }>(
    "/auth/token",
    body,
    { headers: { "Content-Type": "application/x-www-form-urlencoded" } },
  );
  return data.access_token;
}

export async function getMe(): Promise<Me> {
  const { data } = await api.get("/users/me");
  return data;
}

export async function downloadCsv(path: string, filename: string) {
  const base = import.meta.env.VITE_API_BASE_URL || "/api/v1";
  const res = await fetch(`${base}${path}`, {
    headers: {
      Authorization: (api.defaults.headers.common?.Authorization as string) || "",
    },
  });
  if (!res.ok) throw new Error(`Download failed ${res.status}`);
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}
