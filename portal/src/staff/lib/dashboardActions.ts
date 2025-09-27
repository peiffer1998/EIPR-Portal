import api from "../../lib/api";

type TemplateVariables = Record<string, unknown>;

type WaitlistEntry = {
  id: string;
  owner_id?: string | null;
  pet_id?: string | null;
  pet?: { id?: string | null; name?: string | null } | null;
};

async function sendComms(
  endpoint: string,
  payload: { owner_id: string; template_id: string; variables: TemplateVariables },
): Promise<boolean> {
  try {
    await api.post(endpoint, payload);
    return true;
  } catch (error) {
    console.warn("quick comms send failed", error);
    return false;
  }
}

export async function quickSms(
  ownerId: string,
  templateId: string,
  variables: TemplateVariables,
): Promise<boolean> {
  if (!ownerId || !templateId) return false;
  return sendComms("/comms/sms/send", { owner_id: ownerId, template_id: templateId, variables });
}

export async function quickEmail(
  ownerId: string,
  templateId: string,
  variables: TemplateVariables,
): Promise<boolean> {
  if (!ownerId || !templateId) return false;
  return sendComms("/comms/emails/send", { owner_id: ownerId, template_id: templateId, variables });
}

export async function listWaitlistOffered(
  dateISO?: string,
  locationId?: string,
): Promise<WaitlistEntry[]> {
  const params: Record<string, unknown> = { status: "offered", limit: 200 };
  if (dateISO) params.date = dateISO;
  if (locationId) params.location_id = locationId;

  try {
    const { data } = await api.get("/waitlist", { params });
    if (!Array.isArray(data)) return [];
    return data.map((entry: any): WaitlistEntry => ({
      id: String(entry?.id ?? ""),
      owner_id: entry?.owner_id ?? entry?.owner?.id ?? null,
      pet_id: entry?.pet_id ?? entry?.pet?.id ?? null,
      pet: entry?.pet ?? null,
    }));
  } catch (error) {
    console.warn("waitlist offered fetch failed", error);
    return [];
  }
}
