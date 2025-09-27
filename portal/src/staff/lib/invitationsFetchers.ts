import api from "../../lib/api";

const ok = <T>(promise: Promise<{ data: T }>): Promise<T> => promise.then((response) => response.data);

export type InviteRole = "SUPERADMIN" | "ADMIN" | "MANAGER" | "STAFF";

export type Invite = {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  role: InviteRole;
  token?: string;
  status?: "pending" | "sent" | "revoked" | "accepted" | "expired";
  expires_at?: string;
  location_ids?: string[];
};

export async function listInvitations(params?: Record<string, unknown>): Promise<Invite[]> {
  try {
    return await ok<Invite[]>(api.get("/auth/invitations", { params }));
  } catch {
    try {
      return await ok<Invite[]>(api.get("/users/invitations", { params }));
    } catch {
      return [];
    }
  }
}

export async function createInvitation(payload: {
  email: string;
  first_name?: string;
  last_name?: string;
  role: InviteRole;
  location_ids?: string[];
  expires_days?: number;
}): Promise<Invite> {
  try {
    return await ok<Invite>(api.post("/auth/invitations", payload));
  } catch {
    return await ok<Invite>(api.post("/users/invitations", payload));
  }
}

export async function resendInvitation(id: string): Promise<void> {
  try {
    await api.post(`/auth/invitations/${id}/resend`, {});
  } catch {
    await api.post(`/auth/invitations/send`, { id });
  }
}

export async function revokeInvitation(id: string): Promise<void> {
  try {
    await api.delete(`/auth/invitations/${id}`);
  } catch {
    await api.patch(`/auth/invitations/${id}`, { status: "revoked" });
  }
}

export async function acceptInvitation(payload: {
  token: string;
  password: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
}): Promise<void> {
  try {
    await api.post("/auth/invitations/accept", payload);
  } catch {
    await api.post("/auth/accept-invitation", payload);
  }
}

export async function listRoles(): Promise<string[]> {
  try {
    return await ok<string[]>(api.get("/roles"));
  } catch {
    return ["SUPERADMIN", "ADMIN", "MANAGER", "STAFF"];
  }
}
