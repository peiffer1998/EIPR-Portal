import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";

import { listPets } from "../lib/fetchers";

export default function PetPicker({
  ownerId,
  onPick,
}: {
  ownerId?: string;
  onPick: (id: string) => void;
}) {
  const [q, setQ] = useState("");
  const pets = useQuery({
    queryKey: ["pets", ownerId, q],
    queryFn: () => listPets(ownerId, q),
    enabled: Boolean(ownerId) || q.trim().length > 0,
  });

  useEffect(() => {
    if (ownerId && !q) setQ(" ");
  }, [ownerId, q]);

  return (
    <div className="grid gap-1">
      <label className="text-sm text-slate-600">Pet</label>
      <input
        className="border rounded px-3 py-2"
        placeholder="Search"
        value={q}
        onChange={(event) => setQ(event.target.value)}
      />
      {(pets.data || []).slice(0, 8).map((p: any) => (
        <button
          type="button"
          key={p.id}
          className="text-left border rounded px-3 py-2 hover:bg-slate-50"
          onClick={() => onPick(p.id)}
        >
          {p.name} • {p.breed || p.species || "Pet"}
        </button>
      ))}
    </div>
  );
}
