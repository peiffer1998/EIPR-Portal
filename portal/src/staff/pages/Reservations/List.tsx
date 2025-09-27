import { useQuery } from "@tanstack/react-query";

import Button from "../../../ui/Button";
import { Card } from "../../../ui/Card";
import Page from "../../../ui/Page";
import Table from "../../../ui/Table";
import { listReservations } from "../../lib/fetchers";

export default function ReservationsList() {
  const reservations = useQuery({ queryKey: ["resv"], queryFn: () => listReservations({ limit: 50 }) });

  return (
    <Page>
      <Page.Header
        title="Reservations"
        actions={
          <Button as="a" href="/staff/reservations/new">
            New Reservation
          </Button>
        }
      />

      <Card>
        <div className="overflow-auto">
          <Table>
            <thead>
              <tr className="text-left text-slate-500">
                <th className="px-3 py-2">Pet</th>
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Start</th>
                <th className="px-3 py-2">End</th>
              </tr>
            </thead>
            <tbody>
              {(reservations.data || []).map((r: any) => {
                const petLabel = r.pet?.name ?? r.pet_name ?? r.pet_id;
                return (
                  <tr key={r.id} className="border-t">
                    <td className="px-3 py-2">{petLabel}</td>
                    <td className="px-3 py-2 capitalize">{r.reservation_type}</td>
                    <td className="px-3 py-2">{new Date(r.start_at).toLocaleString()}</td>
                    <td className="px-3 py-2">{new Date(r.end_at).toLocaleString()}</td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        </div>
      </Card>
    </Page>
  );
}
