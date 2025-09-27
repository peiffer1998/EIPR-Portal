import { useState } from "react";

import { timeclockPunchIn, timeclockPunchOut } from "../../lib/fetchers";

export default function TimeClock() {
  const [loc, setLoc] = useState(localStorage.getItem("defaultLocationId") || "");

  return (
    <div className="bg-white p-6 rounded-xl shadow grid gap-3 max-w-xl">
      <h3 className="text-xl font-semibold">Time Clock</h3>
      <input
        className="border rounded px-3 py-2"
        placeholder="Location UUID"
        value={loc}
        onChange={(event) => setLoc(event.target.value)}
      />
      <div className="flex gap-2">
        <button
          className="bg-slate-900 text-white px-3 py-2 rounded"
          onClick={async () => {
            await timeclockPunchIn(loc);
            alert("Punched in");
            localStorage.setItem("defaultLocationId", loc);
          }}
          type="button"
        >
          Punch in
        </button>
        <button
          className="bg-slate-900 text-white px-3 py-2 rounded"
          onClick={async () => {
            await timeclockPunchOut();
            alert("Punched out");
          }}
          type="button"
        >
          Punch out
        </button>
      </div>
    </div>
  );
}
