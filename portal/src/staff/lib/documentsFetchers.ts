import api from "../../lib/api";

const ok = <T>(promise: Promise<{ data: T }>): Promise<T> => promise.then((response) => response.data);

export type DocumentRecord = {
  id: string;
  name?: string;
  mime?: string;
  size_bytes?: number;
  owner_id?: string;
  pet_id?: string;
  kind?: string;
  status?: string;
  created_at?: string;
};

export async function listDocuments(params: {
  owner_id?: string;
  pet_id?: string;
  type?: string;
  date_from?: string;
  date_to?: string;
  q?: string;
} = {}): Promise<DocumentRecord[]> {
  try {
    return await ok<DocumentRecord[]>(api.get("/documents", { params }));
  } catch {
    if (params.owner_id) {
      return await ok<DocumentRecord[]>(api.get(`/owners/${params.owner_id}/files`));
    }
    if (params.pet_id) {
      return await ok<DocumentRecord[]>(api.get(`/pets/${params.pet_id}/files`));
    }
    return [];
  }
}

export async function uploadDocument(
  file: File,
  opts: { owner_id?: string; pet_id?: string; kind?: string } = {},
): Promise<DocumentRecord> {
  const form = new FormData();
  form.append("file", file);
  if (opts.owner_id) form.append("owner_id", opts.owner_id);
  if (opts.pet_id) form.append("pet_id", opts.pet_id);
  if (opts.kind) form.append("kind", opts.kind);

  try {
    return await ok<DocumentRecord>(
      api.post("/documents", form, { headers: { "Content-Type": "multipart/form-data" } }),
    );
  } catch {
    if (opts.owner_id) {
      return await ok<DocumentRecord>(api.post(`/owners/${opts.owner_id}/files`, form));
    }
    if (opts.pet_id) {
      return await ok<DocumentRecord>(api.post(`/pets/${opts.pet_id}/files`, form));
    }
    throw new Error("Upload failed");
  }
}

export async function finalizeDocument(id: string): Promise<void> {
  try {
    await api.post(`/documents/${id}/finalize`, {});
  } catch {
    // best-effort: ignore fallback failure
  }
}

export async function deleteDocument(id: string): Promise<void> {
  try {
    await api.delete(`/documents/${id}`);
  } catch {
    // best-effort delete
  }
}

export async function fetchDocumentBlob(id: string): Promise<Blob> {
  const base = import.meta.env.VITE_API_BASE_URL || "/api/v1";
  const response = await fetch(`${base}/documents/${id}`, {
    headers: {
      Authorization: (api.defaults.headers.common?.Authorization as string) || "",
    },
  });
  if (!response.ok) throw new Error("Preview fetch failed");
  return await response.blob();
}

export function buildDocumentLink(id: string): string {
  try {
    return `${window.location.origin}/api/v1/documents/${encodeURIComponent(id)}`;
  } catch {
    return `/api/v1/documents/${id}`;
  }
}
