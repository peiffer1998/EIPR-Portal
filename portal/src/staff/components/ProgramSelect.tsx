import { useEffect, useState } from "react";
import { listPrograms } from "../lib/daycareFetchers";

type Props = {
  locationId?: string;
  value: string;
  onChange: (program: string) => void;
};

export default function ProgramSelect({ locationId, value, onChange }: Props) {
  const [programs, setPrograms] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    if (!locationId) {
      setPrograms([]);
      return () => {
        cancelled = true;
      };
    }

    listPrograms(locationId)
      .then((items) => {
        if (!cancelled) setPrograms(items ?? []);
      })
      .catch(() => {
        if (!cancelled) setPrograms([]);
      });

    return () => {
      cancelled = true;
    };
  }, [locationId]);

  return (
    <select
      className="border rounded px-3 py-2 text-sm"
      value={value}
      onChange={(event) => onChange(event.target.value)}
    >
      <option value="">All programs</option>
      {programs.map((program) => (
        <option key={program} value={program}>
          {program}
        </option>
      ))}
    </select>
  );
}
