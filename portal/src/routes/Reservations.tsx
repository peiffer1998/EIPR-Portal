import type { FormEvent } from 'react';
import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { cancelReservation, requestReservation } from '../lib/portal';
import { usePortalMe } from '../lib/usePortalMe';
import { PORTAL_ME_QUERY_KEY } from '../lib/usePortalMe';

const reservationTypes = [
  { value: 'boarding', label: 'Boarding' },
  { value: 'daycare', label: 'Daycare' },
  { value: 'grooming', label: 'Grooming' },
  { value: 'training', label: 'Training' },
];

const Reservations = () => {
  const queryClient = useQueryClient();
  const { data, isLoading } = usePortalMe();
  const pets = useMemo(() => data?.pets ?? [], [data]);
  const upcoming = useMemo(() => data?.upcoming_reservations ?? [], [data]);
  const past = useMemo(() => data?.past_reservations ?? [], [data]);

  const [form, setForm] = useState({
    petId: pets[0]?.id ?? '',
    reservationType: reservationTypes[0]?.value ?? 'boarding',
    startAt: '',
    endAt: '',
    notes: '',
  });
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (pets.length > 0) {
      setForm((prev) => ({ ...prev, petId: prev.petId || pets[0].id }));
    }
  }, [pets]);

  const requestMutation = useMutation({
    mutationFn: requestReservation,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: PORTAL_ME_QUERY_KEY });
      setSuccess('Reservation request submitted.');
      setError(null);
      setForm((prev) => ({ ...prev, notes: '' }));
    },
    onError: () => {
      setError('Unable to submit reservation. Please verify the details.');
      setSuccess(null);
    },
  });

  const cancelMutation = useMutation({
    mutationFn: cancelReservation,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: PORTAL_ME_QUERY_KEY });
      setSuccess('Reservation cancelled.');
      setError(null);
    },
    onError: () => {
      setError('Unable to cancel this reservation.');
      setSuccess(null);
    },
  });

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form.petId || !form.startAt || !form.endAt) {
      setError('Please select a pet and start/end times.');
      setSuccess(null);
      return;
    }
    const startIso = new Date(form.startAt).toISOString();
    const endIso = new Date(form.endAt).toISOString();
    requestMutation.mutate({
      petId: form.petId,
      reservationType: form.reservationType,
      startAt: startIso,
      endAt: endIso,
      notes: form.notes || undefined,
    });
  };

  const reserveablePets = useMemo(() => pets.map((pet) => ({ id: pet.id, name: pet.name })), [pets]);

  if (isLoading) {
    return <p className="text-slate-500">Loading reservations…</p>;
  }

  if (pets.length === 0) {
    return (
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold text-slate-900">Reservations</h2>
        <p className="text-slate-500">Add a pet with our front desk to request services online.</p>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">Make a Reservation</h2>
        <p className="text-sm text-slate-500">Select your companion, service type, and preferred dates.</p>
        {error && <p className="mt-3 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">{error}</p>}
        {success && <p className="mt-3 rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700">{success}</p>}
        <form className="mt-4 grid gap-4 rounded-2xl bg-white p-6 shadow-sm md:grid-cols-2" onSubmit={handleSubmit}>
          <label className="flex flex-col text-sm font-medium text-slate-700">
            Pet
            <select
              value={form.petId}
              onChange={(event) => setForm((prev) => ({ ...prev, petId: event.target.value }))}
              className="mt-1 rounded-lg border border-slate-300 px-3 py-2 focus:border-orange-500 focus:outline-none"
            >
              {reserveablePets.map((pet) => (
                <option key={pet.id} value={pet.id}>
                  {pet.name}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col text-sm font-medium text-slate-700">
            Service
            <select
              value={form.reservationType}
              onChange={(event) => setForm((prev) => ({ ...prev, reservationType: event.target.value }))}
              className="mt-1 rounded-lg border border-slate-300 px-3 py-2 focus:border-orange-500 focus:outline-none"
            >
              {reservationTypes.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col text-sm font-medium text-slate-700">
            Start
            <input
              type="datetime-local"
              value={form.startAt}
              onChange={(event) => setForm((prev) => ({ ...prev, startAt: event.target.value }))}
              className="mt-1 rounded-lg border border-slate-300 px-3 py-2 focus:border-orange-500 focus:outline-none"
              required
            />
          </label>
          <label className="flex flex-col text-sm font-medium text-slate-700">
            End
            <input
              type="datetime-local"
              value={form.endAt}
              onChange={(event) => setForm((prev) => ({ ...prev, endAt: event.target.value }))}
              className="mt-1 rounded-lg border border-slate-300 px-3 py-2 focus:border-orange-500 focus:outline-none"
              required
            />
          </label>
          <label className="md:col-span-2 flex flex-col text-sm font-medium text-slate-700">
            Notes
            <textarea
              value={form.notes}
              onChange={(event) => setForm((prev) => ({ ...prev, notes: event.target.value }))}
              rows={3}
              className="mt-1 rounded-lg border border-slate-300 px-3 py-2 focus:border-orange-500 focus:outline-none"
              placeholder="Optional instructions"
            />
          </label>
          <button
            type="submit"
            className="md:col-span-2 rounded-lg bg-orange-500 px-4 py-2 font-semibold text-white transition hover:bg-orange-600"
            disabled={requestMutation.isPending}
          >
            {requestMutation.isPending ? 'Submitting…' : 'Request Reservation'}
          </button>
        </form>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-slate-900">Upcoming</h3>
          {upcoming.length === 0 ? (
            <p className="text-sm text-slate-500">No reservations scheduled.</p>
          ) : (
            upcoming.map((reservation) => (
              <div key={reservation.id} className="rounded-2xl bg-white p-4 shadow-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm uppercase text-slate-400">{reservation.reservation_type}</p>
                    <p className="text-base font-semibold text-slate-900">{reservation.pet.name}</p>
                  </div>
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium uppercase text-slate-600">
                    {reservation.status}
                  </span>
                </div>
                <p className="mt-2 text-sm text-slate-500">
                  {new Date(reservation.start_at).toLocaleString()} →{' '}
                  {new Date(reservation.end_at).toLocaleString()}
                </p>
                <div className="mt-3 flex items-center justify-between">
                  <p className="text-xs text-slate-400">{reservation.notes || 'No special notes'}</p>
                  {reservation.status !== 'canceled' && (
                    <button
                      type="button"
                      className="rounded-full bg-slate-900 px-3 py-1 text-xs font-semibold text-white hover:bg-slate-700"
                      onClick={() => cancelMutation.mutate(reservation.id)}
                      disabled={cancelMutation.isPending}
                    >
                      Cancel
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-slate-900">History</h3>
          {past.length === 0 ? (
            <p className="text-sm text-slate-500">No past stays recorded yet.</p>
          ) : (
            past.map((reservation) => (
              <div key={reservation.id} className="rounded-2xl bg-white p-4 shadow-sm">
                <p className="text-sm font-semibold text-slate-900">{reservation.pet.name}</p>
                <p className="text-xs uppercase text-slate-400">{reservation.reservation_type}</p>
                <p className="mt-2 text-sm text-slate-500">
                  {new Date(reservation.start_at).toLocaleDateString()} →{' '}
                  {new Date(reservation.end_at).toLocaleDateString()}
                </p>
                <p className="mt-2 text-xs text-slate-400">Status: {reservation.status}</p>
              </div>
            ))
          )}
        </div>
      </div>
    </section>
  );
};

export default Reservations;
