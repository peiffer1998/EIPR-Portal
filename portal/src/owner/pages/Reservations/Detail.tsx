import { useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import Page from '../../../ui/Page';
import Loading from '../../../ui/Loading';
import { Card, CardHeader } from '../../../ui/Card';
import Button from '../../../ui/Button';
import { fmtDateTime } from '../../../lib/datetime';
import { toast } from '../../../ui/Toast';
import { cancelReservation, reservationDetail } from '../../lib/fetchers';
import type { OwnerReservation } from '../../types';

const OwnerReservationDetail = (): JSX.Element => {
  const { reservationId } = useParams<{ reservationId: string }>();
  const queryClient = useQueryClient();

  const reservationQuery = useQuery({
    queryKey: ['owner', 'reservation', reservationId],
    queryFn: () => reservationDetail(reservationId ?? ''),
    enabled: Boolean(reservationId),
  });

  const cancelMutation = useMutation({
    mutationFn: () => cancelReservation(reservationId ?? ''),
    onSuccess: (next) => {
      queryClient.setQueryData(['owner', 'reservation', reservationId], next);
      queryClient.invalidateQueries({ queryKey: ['owner', 'reservations'] });
      toast('Reservation canceled', 'success');
    },
    onError: () => {
      toast('Unable to cancel reservation. Please call us and we can help.', 'error');
    },
  });

  if (reservationQuery.isLoading || !reservationId) {
    return <Loading text="Loading reservation…" />;
  }

  if (reservationQuery.isError || !reservationQuery.data) {
    return (
      <Page>
        <Page.Header title="Reservation details" />
        <Card>
          <CardHeader title="Reservation not found" sub="We could not load this reservation." />
        </Card>
      </Page>
    );
  }

  const reservation = reservationQuery.data as OwnerReservation;
  const status = reservation.status ?? 'PENDING';
  const statusColor = status === 'CANCELED' ? 'bg-slate-200 text-slate-600' : 'bg-emerald-100 text-emerald-700';

  return (
    <Page>
      <Page.Header title={`Reservation ${reservation.id}`} sub="Details about this booking" />
      <Card className="p-4">
        <CardHeader title="Summary" />
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <div className="text-xs uppercase tracking-wide text-slate-500">Pet</div>
            <div className="text-base font-medium text-slate-800">
              {reservation.pet?.name ?? reservation.pet_id ?? 'Pet'}
            </div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-wide text-slate-500">Type</div>
            <div className="text-base font-medium text-slate-800">
              {reservation.reservation_type ?? 'Reservation'}
            </div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-wide text-slate-500">Start</div>
            <div className="text-base text-slate-800">
              {reservation.start_at ? fmtDateTime(reservation.start_at) : '—'}
            </div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-wide text-slate-500">End</div>
            <div className="text-base text-slate-800">
              {reservation.end_at ? fmtDateTime(reservation.end_at) : '—'}
            </div>
          </div>
        </div>
        <div className="mt-3 flex items-center gap-2">
          <span
            className={`rounded-full px-2 py-1 text-xs font-semibold uppercase ${statusColor}`}
          >
            {status}
          </span>
          {reservation.status !== 'CANCELED' ? (
            <Button
              variant="danger"
              disabled={cancelMutation.isPending}
              onClick={() => cancelMutation.mutate()}
              type="button"
            >
              {cancelMutation.isPending ? 'Canceling…' : 'Cancel reservation'}
            </Button>
          ) : null}
        </div>
      </Card>
    </Page>
  );
};

export default OwnerReservationDetail;
