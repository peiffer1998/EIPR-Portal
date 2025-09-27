import { useEffect, useMemo, useState } from "react";
import { listLocations } from "../lib/adminFetchers";

type Filters = {
  date: string;
  location_id: string;
  area?: string;
  q?: string;
};

type Props = {
  onChange: (filters: Filters) => void;
};

const today = () => new Date().toISOString().slice(0, 10);

export default function BoardFilters({ onChange }: Props) {
  const [date, setDate] = useState<string>(today());
  const [locationId, setLocationId] = useState<string>(localStorage.getItem("defaultLocationId") || "");
  const [area, setArea] = useState<string>("");
  const [query, setQuery] = useState<string>("");
  const [locations, setLocations] = useState<any[]>([]);

  useEffect(() => {
    let cancelled = false;
    listLocations()
      .then((items) => {
        if (!cancelled) setLocations(items ?? []);
      })
      .catch(() => {
        if (!cancelled) setLocations([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const filters = useMemo<Filters>(
    () => ({ date, location_id: locationId, area: area.trim() || undefined, q: query.trim() || undefined }),
    [area, date, locationId, query],
  );

  useEffect(() => {
    onChange(filters);
  }, [filters, onChange]);

  const handleLocationChange = (value: string) => {
    setLocationId(value);
    localStorage.setItem("defaultLocationId", value);
  };

  return (
    <div className="bg-white p-3 rounded-xl shadow flex flex-wrap gap-3 items-end">
      <label className="text-sm grid">
        <span className="text-slate-600">Date</span>
        <input
          type="date"
          className="border rounded px-3 py-2"
          value={date}
          onChange={(event) => setDate(event.target.value)}
        />
      </label>

      <label className="text-sm grid min-w-[220px]">
        <span className="text-slate-600">Location</span>
        <div className="relative">
          <input
            list="staff-board-locations"
            className="border rounded px-3 py-2 w-full"
            value={locationId}
            onChange={(event) => handleLocationChange(event.target.value)}
            placeholder="Location UUID"
          />
          <datalist id="staff-board-locations">
            {locations.map((location) => (
              <option key={location.id} value={location.id}>
                {location.name || location.id}
              </option>
            ))}
          </datalist>
        </div>
      </label>

      <label className="text-sm grid">
        <span className="text-slate-600">Area (optional)</span>
        <input
          className="border rounded px-3 py-2"
          placeholder="Room or zone"
          value={area}
          onChange={(event) => setArea(event.target.value)}
        />
      </label>

      <label className="text-sm grid flex-1 min-w-[160px]">
        <span className="text-slate-600">Search</span>
        <input
          className="border rounded px-3 py-2"
          placeholder="Pet, owner, reservation ID"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>
    </div>
  );
}
