import api from '../../lib/api';
import { readOwner, writeOwner, type StoredOwnerSummary } from '../../lib/storage';
import type {
  OwnerCreditSummary,
  OwnerDocument,
  OwnerGroomingAppointment,
  OwnerInvoice,
  OwnerPackageSummary,
  OwnerPet,
  OwnerPetFile,
  OwnerPreferences,
  OwnerReportCard,
  OwnerReservation,
  OwnerSummary,
} from '../types';

const ownerCache: { id?: string } = {};

export const toStoredOwner = (summary: OwnerSummary): StoredOwnerSummary => ({
  id: summary.id,
  firstName: summary.first_name ?? '',
  lastName: summary.last_name ?? '',
  email: summary.email ?? '',
});

export const fetchMe = async (): Promise<OwnerSummary> => {
  const { data } = await api.get<OwnerSummary>('/users/me');
  if (data?.id) {
    ownerCache.id = data.id;
    writeOwner(toStoredOwner(data));
  }
  return data;
};

const ensureOwnerId = async (): Promise<string> => {
  if (ownerCache.id) return ownerCache.id;
  const stored = readOwner();
  if (stored?.id) {
    ownerCache.id = stored.id;
    return stored.id;
  }
  const me = await fetchMe();
  if (!me.id) {
    throw new Error('Unable to resolve owner');
  }
  return me.id;
};

const ok = async <T>(promise: Promise<{ data: T }>): Promise<T> => {
  const { data } = await promise;
  return data;
};

export const myPets = async (): Promise<OwnerPet[]> => {
  try {
    return await ok(api.get<OwnerPet[]>('/pets', { params: { owner_id: 'me', limit: 200 } }));
  } catch {
    const ownerId = await ensureOwnerId();
    return ok(api.get<OwnerPet[]>(`/owners/${ownerId}/pets`, { params: { limit: 200 } }));
  }
};

export const petDetail = async (petId: string): Promise<OwnerPet> => {
  return ok(api.get<OwnerPet>(`/pets/${petId}`));
};

export const updatePet = async (petId: string, patch: Partial<OwnerPet>): Promise<OwnerPet> => {
  return ok(api.patch<OwnerPet>(`/pets/${petId}`, patch));
};

export const uploadPetFile = async (petId: string, file: File): Promise<OwnerPetFile> => {
  const form = new FormData();
  form.append('file', file);
  return ok(api.post<OwnerPetFile>(`/pets/${petId}/files`, form));
};

export const myReservations = async (): Promise<OwnerReservation[]> => {
  return ok(
    api.get<OwnerReservation[]>('/reservations', {
      params: { owner_id: 'me', limit: 200, order: 'start_at.desc' },
    }),
  );
};

export const reservationDetail = async (reservationId: string): Promise<OwnerReservation> => {
  return ok(api.get<OwnerReservation>(`/reservations/${reservationId}`));
};

export const cancelReservation = async (reservationId: string): Promise<OwnerReservation> => {
  try {
    return await ok(api.post<OwnerReservation>(`/reservations/${reservationId}/cancel`, {}));
  } catch {
    return ok(api.patch<OwnerReservation>(`/reservations/${reservationId}`, { status: 'CANCELED' }));
  }
};

export const myGrooming = async (): Promise<OwnerGroomingAppointment[]> => {
  try {
    return await ok(
      api.get<OwnerGroomingAppointment[]>('/grooming/appointments', {
        params: { owner_id: 'me', limit: 200 },
      }),
    );
  } catch {
    return [];
  }
};

export const myPackages = async (): Promise<OwnerPackageSummary[]> => {
  try {
    const ownerId = await ensureOwnerId();
    return await ok(api.get<OwnerPackageSummary[]>(`/owners/${ownerId}/packages`));
  } catch {
    return [];
  }
};

export const myCredit = async (): Promise<OwnerCreditSummary> => {
  try {
    const ownerId = await ensureOwnerId();
    return await ok(api.get<OwnerCreditSummary>(`/owners/${ownerId}/store-credit`));
  } catch {
    return { balance: 0, ledger: [] };
  }
};

export const myInvoices = async (): Promise<OwnerInvoice[]> => {
  return ok(
    api.get<OwnerInvoice[]>('/invoices', {
      params: { owner_id: 'me', limit: 200, order: 'created_at.desc' },
    }),
  );
};

export const myReportCards = async (): Promise<OwnerReportCard[]> => {
  try {
    return await ok(
      api.get<OwnerReportCard[]>('/report-cards', {
        params: { owner_id: 'me', limit: 200, order: 'occurred_on.desc' },
      }),
    );
  } catch {
    return [];
  }
};

export const myDocuments = async (): Promise<OwnerDocument[]> => {
  try {
    const ownerId = await ensureOwnerId();
    return await ok(api.get<OwnerDocument[]>(`/owners/${ownerId}/files`));
  } catch {
    return [];
  }
};

export const uploadOwnerFile = async (file: File): Promise<OwnerDocument> => {
  const ownerId = await ensureOwnerId();
  const form = new FormData();
  form.append('file', file);
  return ok(api.post<OwnerDocument>(`/owners/${ownerId}/files`, form));
};

export const myPreferences = async (): Promise<OwnerPreferences> => {
  try {
    const ownerId = await ensureOwnerId();
    return await ok(api.get<OwnerPreferences>(`/owners/${ownerId}/preferences`));
  } catch {
    const user = await fetchMe();
    const preferences = user.preferences;
    if (preferences && typeof preferences === 'object') {
      return preferences as OwnerPreferences;
    }
    return { email_opt_in: true, sms_opt_in: true, quiet_hours: '21:00-08:00' };
  }
};

export const updatePreferences = async (
  patch: Partial<OwnerPreferences>,
): Promise<OwnerPreferences> => {
  try {
    const ownerId = await ensureOwnerId();
    return await ok(api.patch<OwnerPreferences>(`/owners/${ownerId}/preferences`, patch));
  } catch {
    return patch as OwnerPreferences;
  }
};
