import api from '../../lib/api';

// Reservation helpers
type ReservationStatus =
  | 'REQUESTED'
  | 'CONFIRMED'
  | 'CHECKED_IN'
  | 'CHECKED_OUT'
  | 'CANCELLED'
  | 'COMPLETED';

type GroomingStatus = 'ARRIVED' | 'IN_PROGRESS' | 'COMPLETE' | 'PICKED_UP';

type ReservationSearchParams = Record<string, unknown>;

type Invoice = {
  id: string;
  total?: number | string;
};

export const getReservation = async (id: string) => {
  const { data } = await api.get(`/reservations/${id}`);
  return data as Record<string, unknown> & {
    id: string;
    status?: ReservationStatus;
  };
};

export const searchReservations = async (params: ReservationSearchParams) => {
  const { data } = await api.get('/reservations', { params });
  return data as Array<Record<string, unknown>>;
};

export const checkInReservation = async (
  id: string,
  body: Record<string, unknown> = {},
) => {
  try {
    const { data } = await api.post(`/reservations/${id}/check-in`, body);
    return data;
  } catch {
    const { data } = await api.patch(`/reservations/${id}`, {
      status: 'CHECKED_IN',
      ...body,
    });
    return data;
  }
};

export const checkOutReservation = async (id: string) => {
  try {
    const { data } = await api.post(`/reservations/${id}/check-out`, {});
    return data;
  } catch {
    const { data } = await api.patch(`/reservations/${id}`, {
      status: 'CHECKED_OUT',
    });
    return data;
  }
};

export const getAppointment = async (id: string) => {
  try {
    const { data } = await api.get(`/grooming/appointments/${id}`);
    return data;
  } catch {
    const { data } = await api.get(`/appointments/${id}`);
    return data;
  }
};

export const setAppointmentStatus = async (id: string, status: GroomingStatus) => {
  try {
    const { data } = await api.post(`/grooming/appointments/${id}/status`, { status });
    return data;
  } catch {
    const { data } = await api.patch(`/grooming/appointments/${id}`, { status });
    return data;
  }
};

export const getInvoiceForReservation = async (id: string) => {
  try {
    const { data } = await api.get('/invoices', {
      params: {
        reservation_id: id,
        limit: 1,
      },
    });
    const invoices = Array.isArray(data) ? data : [];
    return (invoices[0] as Invoice | undefined) ?? null;
  } catch {
    return null;
  }
};

export const captureInvoice = async (invoiceId: string) => {
  try {
    const { data } = await api.post(`/invoices/${invoiceId}/capture`, {});
    return data;
  } catch {
    return null;
  }
};

export const markCashPaid = async (invoiceId: string) => {
  try {
    const { data } = await api.post('/payments', {
      invoice_id: invoiceId,
      amount: null,
      method: 'cash',
    });
    return data;
  } catch {
    const { data } = await api.patch(`/invoices/${invoiceId}`, {
      status: 'PAID',
    });
    return data;
  }
};

export type { GroomingStatus, ReservationStatus };
