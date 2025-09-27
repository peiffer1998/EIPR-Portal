import { useEffect, useState } from 'react';

import { checkOutReservation, searchReservations } from '../lib/fetchers';

type DaycareReservation = Record<string, any> & {
  id: string;
  pet?: { name?: string } | null;
  owner?: { first_name?: string; last_name?: string } | null;
};

export default function DaycareCheckOut() {
  const [today] = useState(() => new Date().toISOString().slice(0, 10));
  const [reservations, setReservations] = useState<DaycareReservation[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const data = await searchReservations({
          date: today,
          reservation_type: 'DAYCARE',
          status: 'CHECKED_IN',
          limit: 200,
        });
        setReservations(data as DaycareReservation[]);
      } catch {
        setReservations([]);
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [today]);

  const handleCheckOut = async (id: string) => {
    try {
      await checkOutReservation(id);
      setReservations((prev) => prev.filter((item) => item.id !== id));
    } catch {
      window.alert('Unable to check out reservation');
    }
  };

  return (
    <div className="grid gap-3">
      <div className="text-2xl font-semibold">Daycare Check-Out — {today}</div>
      {loading ? <div className="text-slate-600">Loading…</div> : null}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-2">
        {reservations.length === 0 && !loading ? (
          <div className="text-slate-600">No daycare guests checked in.</div>
        ) : null}
        {reservations.map((reservation) => (
          <button
            key={reservation.id}
            type="button"
            className="rounded-xl px-4 py-6 text-xl bg-white border hover:bg-slate-50 text-left"
            onClick={() => handleCheckOut(reservation.id)}
          >
            {reservation.pet?.name ?? reservation.id}
            <div className="text-sm text-slate-600">
              {reservation.owner?.first_name ?? ''} {reservation.owner?.last_name ?? ''}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
