import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { listOwners } from "../lib/fetchers";

export default function OwnerPicker({ onPick }: { onPick: (id: string) => void }) {
  const [q, setQ] = useState("");
  const owners = useQuery({
    queryKey: ["owners", q],
    queryFn: () => listOwners(q),
    enabled: q.trim().length > 1,
  });

  return (
    <div className="grid gap-1">
      <label className="text-sm text-slate-600">Owner</label>
      <input
        className="border rounded px-3 py-2"
        placeholder="Search"
        value={q}
        onChange={(event) => setQ(event.target.value)}
      />
      {(owners.data || []).slice(0, 8).map((o: any) => (
        <button
          type="button"
          key={o.id}
          className="text-left border rounded px-3 py-2 hover:bg-slate-50"
          onClick={() => onPick(o.id)}
        >
          {o.first_name} {o.last_name} • {o.email || o.phone || o.id}
        </button>
      ))}
    </div>
  );
}
