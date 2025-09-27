import { useEffect, useMemo, useState } from "react";

import LocationSelect from "../../components/LocationSelect";
import WeeklyHoursGrid from "../../components/WeeklyHoursGrid";
import { getLocationHours, setLocationHours, type DayRow } from "../../lib/hoursFetchers";

const DEFAULT_WEEK: DayRow[] = Array.from({ length: 7 }, (_, index) => ({
  weekday: index,
  is_closed: true,
  open: null,
  close: null,
}));

export default function AdminHours() {
  const [locationId, setLocationId] = useState<string>(() => localStorage.getItem("defaultLocationId") || "");
  const [days, setDays] = useState<DayRow[]>(DEFAULT_WEEK);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string>("");

  useEffect(() => {
    async function load(id: string) {
      setBusy(true);
      setToast("");
      try {
        const response = await getLocationHours(id);
        setDays(response.days ?? DEFAULT_WEEK);
      } finally {
        setBusy(false);
      }
    }

    if (locationId) {
      void load(locationId);
    }
  }, [locationId]);

  const canSave = useMemo(() => Boolean(locationId) && !busy, [locationId, busy]);

  async function handleSave() {
    if (!locationId || busy) return;
    setBusy(true);
    setToast("");
    try {
      await setLocationHours(locationId, days);
      setToast("Saved");
    } finally {
      setBusy(false);
    }
  }

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
        <div className="ml-auto flex items-center gap-3 text-sm">
          {toast && <span className="text-green-700">{toast}</span>}
          <button
            className="px-3 py-2 rounded bg-slate-900 text-white disabled:opacity-60"
            type="button"
            onClick={handleSave}
            disabled={!canSave}
          >
            {busy ? "Saving…" : "Save All"}
          </button>
        </div>
      </div>

      {!locationId ? (
        <div className="text-sm text-slate-500">Select a location to configure weekly hours.</div>
      ) : (
        <WeeklyHoursGrid initial={days} onChange={setDays} />
      )}
    </div>
  );
}
