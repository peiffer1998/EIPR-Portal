import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { buildCommissions, listCommissions } from "../../lib/fetchers";

export default function Commissions() {
  const [from, setFrom] = useState(new Date(Date.now() - 7 * 864e5).toISOString().slice(0, 10));
  const [to, setTo] = useState(new Date().toISOString().slice(0, 10));
  const rows = useQuery({ queryKey: ["commissions"], queryFn: () => listCommissions() });

  return (
    <div className="bg-white p-6 rounded-xl shadow">
      <h3 className="text-xl font-semibold">Commissions</h3>
      <div className="flex gap-2 mb-3">
        <input
          type="date"
          className="border rounded px-3 py-2"
          value={from}
          onChange={(event) => setFrom(event.target.value)}
        />
        <input
          type="date"
          className="border rounded px-3 py-2"
          value={to}
          onChange={(event) => setTo(event.target.value)}
        />
        <button
          className="bg-slate-900 text-white px-3 py-2 rounded"
          onClick={async () => {
            await buildCommissions(from, to);
            await rows.refetch();
          }}
          type="button"
        >
          Build
        </button>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-slate-500">
            <th>Appointment</th>
            <th>Specialist</th>
            <th>Amount</th>
          </tr>
        </thead>
        <tbody>
          {(rows.data || []).map((r: any) => (
            <tr key={r.id} className="border-t">
              <td className="py-2">{r.appointment_id}</td>
              <td>{r.specialist_id}</td>
              <td>{r.commission_amount}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
