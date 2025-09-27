import { useQuery } from '@tanstack/react-query';

import Page from '../../ui/Page';
import Loading from '../../ui/Loading';
import Table from '../../ui/Table';
import { Card, CardHeader } from '../../ui/Card';
import { fmtDateTime } from '../../lib/datetime';
import { myGrooming } from '../lib/fetchers';
import type { OwnerGroomingAppointment } from '../types';

const OwnerGrooming = (): JSX.Element => {
  const groomingQuery = useQuery({ queryKey: ['owner', 'grooming'], queryFn: myGrooming });

  if (groomingQuery.isLoading) {
    return <Loading text="Loading grooming appointments…" />;
  }

  if (groomingQuery.isError) {
    return (
      <Page>
        <Page.Header title="Grooming" />
        <Card>
          <CardHeader title="Unable to load appointments" sub="Please refresh or contact the resort." />
        </Card>
      </Page>
    );
  }

  const appointments = groomingQuery.data ?? [];

  return (
    <Page>
      <Page.Header title="Grooming" sub="Upcoming grooming appointments" />
      <Card className="p-0 overflow-hidden">
        <CardHeader title="Appointments" sub={`Total: ${appointments.length}`} />
        <div className="overflow-x-auto">
          <Table>
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="px-3 py-2">Pet</th>
                <th className="px-3 py-2">Service</th>
                <th className="px-3 py-2">Start</th>
                <th className="px-3 py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {appointments.length ? (
                appointments.map((appt: OwnerGroomingAppointment) => (
                  <tr key={appt.id} className="border-t border-slate-100 text-sm">
                    <td className="px-3 py-2">{appt.pet?.name ?? appt.pet_id ?? 'Pet'}</td>
                    <td className="px-3 py-2">{appt.service?.name ?? 'Service'}</td>
                    <td className="px-3 py-2">
                      {appt.start_at ? fmtDateTime(appt.start_at) : '—'}
                    </td>
                    <td className="px-3 py-2">
                      <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-medium uppercase text-slate-600">
                        {appt.status ?? 'Scheduled'}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="px-3 py-6 text-center text-sm text-slate-500">
                    No grooming appointments scheduled yet.
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

export default OwnerGrooming;
