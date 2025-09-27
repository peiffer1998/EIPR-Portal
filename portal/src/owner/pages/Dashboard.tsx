import { useQuery } from '@tanstack/react-query';

import Page from '../../ui/Page';
import Loading from '../../ui/Loading';
import { Card, CardHeader } from '../../ui/Card';
import Table from '../../ui/Table';
import { fmtDateTime } from '../../lib/datetime';
import { myGrooming, myPets, myReservations } from '../lib/fetchers';
import type { OwnerReservation } from '../types';

const OwnerDashboard = (): JSX.Element => {
  const petsQuery = useQuery({ queryKey: ['owner', 'pets'], queryFn: myPets });
  const reservationsQuery = useQuery({ queryKey: ['owner', 'reservations'], queryFn: myReservations });
  const groomingQuery = useQuery({ queryKey: ['owner', 'grooming'], queryFn: myGrooming });

  if (petsQuery.isLoading || reservationsQuery.isLoading || groomingQuery.isLoading) {
    return <Loading text="Loading your dashboard…" />;
  }

  if (petsQuery.isError || reservationsQuery.isError || groomingQuery.isError) {
    return (
      <Page>
        <Page.Header title="Dashboard" sub="Overview" />
        <Card>
          <CardHeader title="Something went wrong" sub="We could not load your latest data." />
          <p className="text-sm text-slate-500">
            Please refresh the page. If the problem continues, contact the resort so we can help.
          </p>
        </Card>
      </Page>
    );
  }

  const pets = petsQuery.data ?? [];
  const reservations = reservationsQuery.data ?? [];
  const activeReservations = reservations.filter((reservation) => reservation.status !== 'CANCELED');
  const displayedReservations = activeReservations.slice(0, 5);
  const upcomingCount = activeReservations.length;
  const grooming = groomingQuery.data ?? [];

  return (
    <Page>
      <Page.Header title="Dashboard" sub="Overview of your pets and bookings" />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <Card className="p-4">
          <div className="text-sm font-medium text-slate-500">My pets</div>
          <div className="mt-2 text-3xl font-semibold text-slate-900">{pets.length}</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm font-medium text-slate-500">Upcoming reservations</div>
          <div className="mt-2 text-3xl font-semibold text-slate-900">{upcomingCount}</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm font-medium text-slate-500">Upcoming grooming</div>
          <div className="mt-2 text-3xl font-semibold text-slate-900">{grooming.length}</div>
        </Card>
      </div>
      <Card className="p-0 overflow-hidden">
        <CardHeader title="Recent reservations" sub="Last five reservations with statuses" />
        <div className="overflow-x-auto">
          <Table>
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Pet</th>
                <th className="px-3 py-2">Start</th>
                <th className="px-3 py-2">End</th>
                <th className="px-3 py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {displayedReservations.length ? (
                displayedReservations.map((reservation: OwnerReservation) => (
                  <tr key={reservation.id} className="border-t border-slate-100 text-sm">
                    <td className="px-3 py-2 capitalize">{reservation.reservation_type ?? 'Reservation'}</td>
                    <td className="px-3 py-2">{reservation.pet?.name ?? reservation.pet_id ?? 'Pet'}</td>
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
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="px-3 py-6 text-center text-sm text-slate-500">
                    No recent reservations yet. Once you book, they will appear here.
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

export default OwnerDashboard;
