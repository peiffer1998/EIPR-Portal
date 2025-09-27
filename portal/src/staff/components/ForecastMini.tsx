import React from "react";
import { Link } from "react-router-dom";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
  Legend,
} from "recharts";

import {
  getBoardingAvailability,
  getDaycareCounts,
  getGroomingCounts,
  type DailyAvailability,
} from "../lib/forecastFetchers";

const DAYS = 7;

function formatLabel(dateIso: string) {
  const date = new Date(`${dateIso}T00:00:00`);
  return `${date.getMonth() + 1}/${date.getDate()}`;
}

export default function ForecastMini({
  startISO,
  locationId,
}: {
  startISO: string;
  locationId?: string;
}) {
  const [boarding, setBoarding] = React.useState<DailyAvailability[] | null>(null);
  const [daycare, setDaycare] = React.useState<{ date: string; count: number }[] | null>(null);
  const [grooming, setGrooming] = React.useState<{ date: string; count: number }[] | null>(null);

  React.useEffect(() => {
    let cancelled = false;

    async function load() {
      setBoarding(null);
      setDaycare(null);
      setGrooming(null);

      try {
        const [boardingData, daycareData, groomingData] = await Promise.all([
          getBoardingAvailability(locationId, startISO, DAYS),
          getDaycareCounts(locationId, startISO, DAYS),
          getGroomingCounts(locationId, startISO, DAYS),
        ]);
        if (!cancelled) {
          setBoarding(boardingData);
          setDaycare(daycareData);
          setGrooming(groomingData);
        }
      } catch (error) {
        console.warn("forecast mini load failed", error);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [startISO, locationId]);

  const boardingData = React.useMemo(
    () =>
      boarding?.map((entry) => ({
        date: formatLabel(entry.date),
        booked: entry.booked,
        capacity: entry.capacity ?? undefined,
      })) ?? [],
    [boarding],
  );

  const daycareData = React.useMemo(
    () => daycare?.map((entry) => ({ date: formatLabel(entry.date), count: entry.count })) ?? [],
    [daycare],
  );

  const groomingData = React.useMemo(
    () => grooming?.map((entry) => ({ date: formatLabel(entry.date), count: entry.count })) ?? [],
    [grooming],
  );

  return (
    <section className="rounded-xl bg-white p-4 shadow">
      <header className="mb-3 flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">Forecast</p>
          <h2 className="text-lg font-semibold text-slate-900">Next 7 Days</h2>
        </div>
        <Link
          className="text-sm font-medium text-blue-700 transition hover:text-blue-900"
          to="/staff/reports/availability"
        >
          Open Availability Report
        </Link>
      </header>

      <div className="grid gap-4 lg:grid-cols-3">
        <article className="rounded-lg border border-slate-200 p-3">
          <h3 className="text-sm font-semibold text-slate-800">Boarding · Occupancy</h3>
          <div className="mt-2 h-36">
            {boarding ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={boardingData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="#94a3b8" />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} stroke="#94a3b8" />
                  <Tooltip />
                  <Legend verticalAlign="top" height={24} />
                  <Area type="monotone" dataKey="booked" stroke="#6366f1" fill="#6366f1" fillOpacity={0.3} name="Booked" />
                  {boardingData.some((entry) => entry.capacity != null) ? (
                    <Area type="monotone" dataKey="capacity" stroke="#f97316" fill="#f97316" fillOpacity={0.15} name="Capacity" />
                  ) : null}
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-slate-500">Loading…</div>
            )}
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Capacity plots when available, otherwise fallback shows booked counts only.
          </p>
        </article>

        <article className="rounded-lg border border-slate-200 p-3">
          <h3 className="text-sm font-semibold text-slate-800">Daycare · Expected</h3>
          <div className="mt-2 h-36">
            {daycare ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={daycareData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="#94a3b8" />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} stroke="#94a3b8" />
                  <Tooltip />
                  <Bar dataKey="count" name="Count" fill="#14b8a6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-slate-500">Loading…</div>
            )}
          </div>
        </article>

        <article className="rounded-lg border border-slate-200 p-3">
          <h3 className="text-sm font-semibold text-slate-800">Grooming · Appointments</h3>
          <div className="mt-2 h-36">
            {grooming ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={groomingData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="#94a3b8" />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} stroke="#94a3b8" />
                  <Tooltip />
                  <Bar dataKey="count" name="Count" fill="#f97316" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-slate-500">Loading…</div>
            )}
          </div>
        </article>
      </div>
    </section>
  );
}
