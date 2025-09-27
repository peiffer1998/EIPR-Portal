import { useEffect, useState } from "react";

import ClosureForm from "../../components/ClosureForm";
import ClosureList from "../../components/ClosureList";
import LocationSelect from "../../components/LocationSelect";
import { createClosure, deleteClosure, listClosures } from "../../lib/hoursFetchers";

export default function AdminClosures() {
  const [locationId, setLocationId] = useState<string>(() => localStorage.getItem("defaultLocationId") || "");
  const [rows, setRows] = useState<Array<{ id?: string; start_date: string; end_date: string; reason?: string }>>([]);
  const [busy, setBusy] = useState(false);

  async function load(id: string) {
    setBusy(true);
    try {
      setRows(await listClosures(id));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (locationId) {
      void load(locationId);
    }
  }, [locationId]);

  return (
    <div className="grid gap-3">
      <div className="bg-white p-3 rounded-xl shadow flex items-center gap-2">
        <span className="text-sm text-slate-600">Location</span>
        <LocationSelect
          value={locationId}
          onChange={(id) => {
            setLocationId(id);
            localStorage.setItem("defaultLocationId", id);
          }}
        />
        <span className="ml-auto text-sm text-slate-500">{busy ? "Loading…" : ""}</span>
      </div>

      {!locationId ? (
        <div className="text-sm text-slate-500">Select a location to manage closures.</div>
      ) : (
        <>
          <ClosureForm
            onCreate={async (values) => {
              await createClosure(locationId, values);
              await load(locationId);
            }}
          />
          <ClosureList
            rows={rows}
            onDelete={async (id) => {
              await deleteClosure(locationId, id);
              await load(locationId);
            }}
          />
        </>
      )}
    </div>
  );
}
