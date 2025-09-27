import { useState } from "react";

import { downloadCsv } from "../../lib/staffApi";
import { P } from "../../lib/paths";

export default function Reports() {
  const [from, setFrom] = useState(new Date(Date.now() - 7 * 864e5).toISOString().slice(0, 10));
  const [to, setTo] = useState(new Date().toISOString().slice(0, 10));

  const btn = (label: string, path: string) => (
    <button
      className="bg-slate-900 text-white px-3 py-2 rounded"
      onClick={() => downloadCsv(path, `${label}_${from}_${to}.csv`)}
      type="button"
    >
      {label}
    </button>
  );

  return (
    <div className="bg-white p-6 rounded-xl shadow grid gap-3 max-w-2xl">
      <h3 className="text-xl font-semibold">Reports</h3>
      <div className="grid grid-cols-2 gap-2">
        <label className="text-sm">
          From
          <input
            type="date"
            value={from}
            onChange={(event) => setFrom(event.target.value)}
            className="border rounded px-3 py-2 w-full"
          />
        </label>
        <label className="text-sm">
          To
          <input
            type="date"
            value={to}
            onChange={(event) => setTo(event.target.value)}
            className="border rounded px-3 py-2 w-full"
          />
        </label>
      </div>
      <div className="grid gap-2">
        {btn("Revenue", P.reportsMax.revenue(from, to))}
        {btn("Occupancy", P.reportsMax.occupancy(from, to))}
        {btn("Payments", P.reportsMax.payments(from, to))}
        {btn("Deposits", P.reportsMax.deposits(from, to))}
        {btn("Commissions", P.reportsMax.commissions(from, to))}
        {btn("Tips", P.reportsMax.tips(from, to))}
      </div>
    </div>
  );
}
