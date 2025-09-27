import { useEffect, useMemo, useState } from "react";

import { listLocations } from "../lib/adminFetchers";
import { getServices } from "../lib/groomingFetchers";

type Filters = {
  date: string;
  location_id: string;
  service_id?: string;
  q?: string;
};

type Props = {
  onChange: (filters: Filters) => void;
};

const today = () => new Date().toISOString().slice(0, 10);

export default function GroomingFilters({ onChange }: Props) {
  const [date, setDate] = useState<string>(today());
  const [locationId, setLocationId] = useState<string>(localStorage.getItem("defaultLocationId") || "");
  const [serviceId, setServiceId] = useState<string>("");
  const [query, setQuery] = useState<string>("");
  const [locations, setLocations] = useState<any[]>([]);
  const [services, setServices] = useState<any[]>([]);

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

  useEffect(() => {
    if (!locationId) {
      setServices([]);
      return;
    }
    let cancelled = false;
    getServices(locationId)
      .then((items) => {
        if (!cancelled) setServices(items ?? []);
      })
      .catch(() => {
        if (!cancelled) setServices([]);
      });
    return () => {
      cancelled = true;
    };
  }, [locationId]);

  const filters = useMemo<Filters>(
    () => ({
      date,
      location_id: locationId,
      service_id: serviceId || undefined,
      q: query.trim() || undefined,
    }),
    [date, locationId, query, serviceId],
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
            list="grooming-board-locations"
            className="border rounded px-3 py-2 w-full"
            value={locationId}
            onChange={(event) => handleLocationChange(event.target.value)}
            placeholder="Location UUID"
          />
          <datalist id="grooming-board-locations">
            {locations.map((location) => (
              <option key={location.id} value={location.id}>
                {location.name || location.id}
              </option>
            ))}
          </datalist>
        </div>
      </label>

      <label className="text-sm grid min-w-[200px]">
        <span className="text-slate-600">Service</span>
        <select
          className="border rounded px-3 py-2"
          value={serviceId}
          onChange={(event) => setServiceId(event.target.value)}
        >
          <option value="">All services</option>
          {services.map((service) => (
            <option key={service.id} value={service.id}>
              {service.name || service.id}
            </option>
          ))}
        </select>
      </label>

      <label className="text-sm grid flex-1 min-w-[160px]">
        <span className="text-slate-600">Search</span>
        <input
          className="border rounded px-3 py-2"
          placeholder="Pet or owner"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>
    </div>
  );
}
