import { useQuery } from "@tanstack/react-query";

import { listReservations } from "../../lib/fetchers";

export default function ReservationsList() {
  const reservations = useQuery({ queryKey: ["resv"], queryFn: () => listReservations({ limit: 50 }) });

  return (
    <div className="bg-white p-6 rounded-xl shadow">
      <h3 className="text-xl font-semibold mb-2">Reservations</h3>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-slate-500">
            <th>Pet</th>
            <th>Type</th>
            <th>Start</th>
            <th>End</th>
          </tr>
        </thead>
        <tbody>
          {(reservations.data || []).map((r: any) => (
            <tr key={r.id} className="border-t">
              <td className="py-2">{r.pet_id}</td>
              <td>{r.reservation_type}</td>
              <td>{new Date(r.start_at).toLocaleString()}</td>
              <td>{new Date(r.end_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
