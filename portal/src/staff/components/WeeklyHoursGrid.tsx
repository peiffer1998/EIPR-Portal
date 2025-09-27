import { useEffect, useState } from "react";

import type { DayRow } from "../lib/hoursFetchers";

const LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

interface Props {
  initial: DayRow[];
  onChange: (days: DayRow[]) => void;
}

export default function WeeklyHoursGrid({ initial, onChange }: Props) {
  const [days, setDays] = useState<DayRow[]>(initial);

  useEffect(() => {
    setDays(initial);
  }, [initial]);

  function update(index: number, patch: Partial<DayRow>) {
    const next = days.map((day, idx) => (idx === index ? { ...day, ...patch } : day));
    setDays(next);
    onChange(next);
  }

  return (
    <div className="bg-white rounded-xl shadow overflow-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-slate-500">
            <th className="px-3 py-2">Day</th>
            <th>Closed</th>
            <th>Open</th>
            <th>Close</th>
          </tr>
        </thead>
        <tbody>
          {days.map((day, index) => (
            <tr key={day.weekday} className="border-t">
              <td className="px-3 py-2">{LABELS[index] ?? day.weekday}</td>
              <td>
                <input
                  type="checkbox"
                  checked={Boolean(day.is_closed)}
                  onChange={(event) => update(index, { is_closed: event.target.checked })}
                />
              </td>
              <td>
                <input
                  className="border rounded px-2 py-1"
                  type="time"
                  value={day.open ?? ""}
                  onChange={(event) => update(index, { open: event.target.value || null })}
                  disabled={day.is_closed}
                />
              </td>
              <td>
                <input
                  className="border rounded px-2 py-1"
                  type="time"
                  value={day.close ?? ""}
                  onChange={(event) => update(index, { close: event.target.value || null })}
                  disabled={day.is_closed}
                />
              </td>
            </tr>
          ))}
          {days.length === 0 && (
            <tr>
              <td colSpan={4} className="px-3 py-4 text-sm text-slate-500">
                No hours configured
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
