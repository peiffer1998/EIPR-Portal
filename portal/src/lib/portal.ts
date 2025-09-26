import api from './api';

export interface ApiUserSummary {
  first_name: string;
  last_name: string;
  email: string;
}

export interface ApiOwnerSummary {
  id: string;
  preferred_contact_method: string | null;
  user: ApiUserSummary;
}

export interface ApiPet {
  id: string;
  name: string;
  pet_type: string;
  immunization_records: Array<{
    id: string;
    status: string;
    immunization_type: { name: string } | null;
    expires_on: string | null;
  }>;
}

export interface ApiReservation {
  id: string;
  reservation_type: string;
  status: string;
  start_at: string;
  end_at: string;
  notes: string | null;
  pet: ApiPet;
}

export interface ApiInvoiceItem {
  description: string;
  amount: string;
}

export interface ApiInvoice {
  id: string;
  status: string;
  subtotal: string;
  total: string;
  discount_total: string;
  tax_total: string;
  created_at: string;
  paid_at: string | null;
  items?: ApiInvoiceItem[];
}

export interface ApiDocument {
  id: string;
  file_name: string;
  url: string | null;
  url_web?: string | null;
  content_type: string | null;
  created_at: string;
}

export interface PortalMeApiResponse {
  owner: ApiOwnerSummary;
  pets: ApiPet[];
  upcoming_reservations: ApiReservation[];
  past_reservations: ApiReservation[];
  unpaid_invoices: ApiInvoice[];
  recent_paid_invoices: ApiInvoice[];
  documents?: ApiDocument[];
}

export interface PortalInvoicesResponse {
  unpaid: ApiInvoice[];
  recent_paid: ApiInvoice[];
}

export const fetchPortalMe = async (): Promise<PortalMeApiResponse> => {
  const { data } = await api.get<PortalMeApiResponse>('/portal/me');
  return data;
};

export const requestReservation = async (payload: {
  petId: string;
  reservationType: string;
  startAt: string;
  endAt: string;
  notes?: string;
}) => {
  const { data } = await api.post<ApiReservation>('/portal/reservations/request', {
    pet_id: payload.petId,
    reservation_type: payload.reservationType,
    start_at: payload.startAt,
    end_at: payload.endAt,
    notes: payload.notes,
  });
  return data;
};

export const cancelReservation = async (reservationId: string) => {
  const { data } = await api.post<ApiReservation>(`/portal/reservations/${reservationId}/cancel`);
  return data;
};

export const fetchInvoices = async (): Promise<PortalInvoicesResponse> => {
  const { data } = await api.get<PortalInvoicesResponse>('/portal/invoices');
  return data;
};

export const createPaymentIntent = async (invoiceId: string) => {
  const { data } = await api.post<{ client_secret: string; transaction_id: string; invoice_id: string }>(
    '/portal/payments/create-intent',
    {
      invoice_id: invoiceId,
    },
  );
  return data;
};

export const presignDocument = async (payload: {
  filename: string;
  contentType: string;
  ownerId?: string;
  petId?: string;
}) => {
  const { data } = await api.post<{ upload_ref: string; upload_url: string; headers: Record<string, string> }>(
    '/portal/documents/presign',
    {
      filename: payload.filename,
      content_type: payload.contentType,
      owner_id: payload.ownerId,
      pet_id: payload.petId,
    },
  );
  return data;
};

export const finalizeDocument = async (payload: {
  uploadRef: string;
  ownerId?: string;
  petId?: string;
}) => {
  const { data } = await api.post<{ document: unknown }>('/portal/documents/finalize', {
    upload_ref: payload.uploadRef,
    owner_id: payload.ownerId,
    pet_id: payload.petId,
  });
  return data;
};
