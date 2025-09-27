import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import Page from '../../../ui/Page';
import Loading from '../../../ui/Loading';
import Table from '../../../ui/Table';
import { Card, CardHeader } from '../../../ui/Card';
import { fmtDateTime } from '../../../lib/datetime';
import { myReservations } from '../../lib/fetchers';
import type { OwnerReservation } from '../../types';

const OwnerReservations = (): JSX.Element => {
  const reservationsQuery = useQuery({ queryKey: ['owner', 'reservations'], queryFn: myReservations });

  if (reservationsQuery.isLoading) {
    return <Loading text="Loading reservations…" />;
  }

  if (reservationsQuery.isError) {
    return (
      <Page>
        <Page.Header title="Reservations" />
        <Card>
          <CardHeader title="Unable to load reservations" sub="Please refresh or try again later." />
        </Card>
      </Page>
    );
  }

  const reservations = reservationsQuery.data ?? [];

  return (
    <Page>
      <Page.Header
        title="Reservations"
        sub="View upcoming and past reservations. Contact the resort if anything looks incorrect."
      />
      <Card className="p-0 overflow-hidden">
        <CardHeader title="All reservations" sub={`Total: ${reservations.length}`} />
        <div className="overflow-x-auto">
          <Table>
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Pet</th>
                <th className="px-3 py-2">Start</th>
                <th className="px-3 py-2">End</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {reservations.length ? (
                reservations.map((reservation: OwnerReservation) => (
                  <tr key={reservation.id} className="border-t border-slate-100 text-sm">
                    <td className="px-3 py-2 capitalize">{reservation.reservation_type ?? 'Reservation'}</td>
                    <td className="px-3 py-2">{reservation.pet?.name ?? reservation.pet_id ?? '—'}</td>
                    <td className="px-3 py-2">
                      {reservation.start_at ? fmtDateTime(reservation.start_at) : '—'}
                    </td>
                    <td className="px-3 py-2">
                      {reservation.end_at ? fmtDateTime(reservation.end_at) : '—'}
                    </td>
                    <td className="px-3 py-2">
                      <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-medium uppercase text-slate-600">
                        {reservation.status ?? 'Pending'}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <Link className="text-sm font-medium text-orange-600" to={`/owner/reservations/${reservation.id}`}>
                        Details
                      </Link>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="px-3 py-6 text-center text-sm text-slate-500">
                    You have no reservations yet. When you book, they will appear here.
                  </td>
                </tr>
              )}
            </tbody>
          </Table>
        </div>
      </Card>
    </Page>
  );
};

export default OwnerReservations;
