import { useState } from 'react';

import ScanBox from '../components/ScanBox';
import { checkInReservation, getReservation } from '../lib/fetchers';

type Reservation = Record<string, any> & {
  id: string;
  pet?: { name?: string } | null;
  pet_id?: string;
  reservation_type?: string;
};

export default function BoardingCheckIn() {
  const [reservation, setReservation] = useState<Reservation | null>(null);
  const [locationId, setLocationId] = useState('');
  const [runId, setRunId] = useState('');
  const [loading, setLoading] = useState(false);

  const loadReservation = async (id: string) => {
    setLoading(true);
    try {
      const result = await getReservation(id);
      setReservation(result as Reservation);
    } catch {
      window.alert('Unable to load reservation');
      setReservation(null);
    } finally {
      setLoading(false);
    }
  };

  const handleCheckIn = async () => {
    if (!reservation) return;
    setLoading(true);
    try {
      await checkInReservation(reservation.id, {
        location_id: locationId || undefined,
        run_id: runId || undefined,
      });
      window.alert('Reservation checked in');
      setReservation(null);
      setLocationId('');
      setRunId('');
    } catch {
      window.alert('Check-in failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid gap-4">
      <ScanBox label="Scan or type reservation ID" onSubmit={loadReservation} />
      {loading ? <div className="text-slate-600">Working…</div> : null}
      {reservation ? (
        <div className="grid gap-2">
          <div className="text-2xl font-semibold">
            {reservation.pet?.name ?? reservation.pet_id} • {reservation.reservation_type ?? 'Boarding'}
          </div>
          <div className="grid md:grid-cols-3 gap-2">
            <label className="text-lg grid">
              <span className="text-sm text-slate-600">Location (optional)</span>
              <input
                className="text-xl border rounded px-3 py-2"
                value={locationId}
                onChange={(event) => setLocationId(event.target.value)}
                placeholder="Location ID"
              />
            </label>
            <label className="text-lg grid">
              <span className="text-sm text-slate-600">Run (optional)</span>
              <input
                className="text-xl border rounded px-3 py-2"
                value={runId}
                onChange={(event) => setRunId(event.target.value)}
                placeholder="Run ID"
              />
            </label>
            <a
              className="text-xl rounded px-4 py-3 bg-slate-900 text-white mt-6 text-center"
              href={`/staff/print/run-card/${reservation.id}`}
              target="_blank"
              rel="noreferrer"
            >
              Print Run Card
            </a>
          </div>
          <div className="flex gap-3 mt-2">
            <button
              type="button"
              className="px-5 py-4 rounded bg-orange-500 text-white text-xl"
              onClick={handleCheckIn}
              disabled={loading}
            >
              Check In
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
