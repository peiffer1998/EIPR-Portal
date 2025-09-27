import { useState } from "react";

import { openPeriod, lockPeriod, markPaid } from "../../lib/fetchers";

export default function Payroll() {
  const [from, setFrom] = useState(new Date(Date.now() - 7 * 864e5).toISOString().slice(0, 10));
  const [to, setTo] = useState(new Date().toISOString().slice(0, 10));
  const [loc, setLoc] = useState(localStorage.getItem("defaultLocationId") || "");

  return (
    <div className="bg-white p-6 rounded-xl shadow grid gap-3 max-w-2xl">
      <h3 className="text-xl font-semibold">Payroll periods</h3>
      <div className="grid md:grid-cols-3 gap-2">
        <label className="text-sm">
          From
          <input
            type="date"
            className="border rounded px-3 py-2 w-full"
            value={from}
            onChange={(event) => setFrom(event.target.value)}
          />
        </label>
        <label className="text-sm">
          To
          <input
            type="date"
            className="border rounded px-3 py-2 w-full"
            value={to}
            onChange={(event) => setTo(event.target.value)}
          />
        </label>
        <input
          className="border rounded px-3 py-2"
          placeholder="Location UUID optional"
          value={loc}
          onChange={(event) => setLoc(event.target.value)}
        />
      </div>
      <div className="flex gap-2">
        <button
          className="bg-slate-900 text-white px-3 py-2 rounded"
          onClick={async () => {
            const period = await openPeriod({
              starts_on: from,
              ends_on: to,
              location_id: loc || null,
            });
            alert(`Opened ${period.id}`);
          }}
          type="button"
        >
          Open
        </button>
        <button
          className="bg-slate-900 text-white px-3 py-2 rounded"
          onClick={async () => {
            const id = prompt("Period ID to lock");
            if (id) {
              await lockPeriod(id);
              alert("Locked");
            }
          }}
          type="button"
        >
          Lock
        </button>
        <button
          className="bg-slate-900 text-white px-3 py-2 rounded"
          onClick={async () => {
            const id = prompt("Period ID to mark paid");
            if (id) {
              await markPaid(id);
              alert("Paid");
            }
          }}
          type="button"
        >
          Mark paid
        </button>
      </div>
    </div>
  );
}
