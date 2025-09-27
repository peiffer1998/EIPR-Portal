import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";

import { listOwners, listPets } from "../lib/fetchers";

export default function StaffSearchBar() {
  const [q, setQ] = useState("");
  const navigate = useNavigate();
  const show = q.trim().length > 1;
  const owners = useQuery({
    queryKey: ["own", q],
    queryFn: () => listOwners(q),
    enabled: show,
  });
  const pets = useQuery({
    queryKey: ["pet", q],
    queryFn: () => listPets(undefined, q),
    enabled: show,
  });

  const ownerRows = (owners.data || []).slice(0, 6);
  const petRows = (pets.data || []).slice(0, 6);

  return (
    <div className="relative">
      <div className="flex items-center gap-2 bg-white border rounded px-3 py-2 w-[340px]">
        <Search size={16} className="text-slate-500" />
        <input
          value={q}
          onChange={(event) => setQ(event.target.value)}
          placeholder="Search owners or pets"
          className="outline-none text-sm flex-1"
        />
      </div>
      {show && (ownerRows.length || petRows.length) ? (
        <div className="absolute z-20 mt-1 bg-white border rounded shadow w-[340px] max-h-72 overflow-auto">
          <div className="px-3 pt-2 text-xs text-slate-500">Owners</div>
          {ownerRows.map((o: any) => (
            <button
              key={o.id}
              onClick={() => navigate(`/staff/customers/${o.id}`)}
              className="block w-full text-left px-3 py-2 hover:bg-slate-50"
              type="button"
            >
              {o.first_name} {o.last_name} • {o.email || o.phone || o.id}
            </button>
          ))}
          <div className="px-3 pt-2 text-xs text-slate-500">Pets</div>
          {petRows.map((p: any) => (
            <button
              key={p.id}
              onClick={() => navigate(`/staff/pets/${p.id}`)}
              className="block w-full text-left px-3 py-2 hover:bg-slate-50"
              type="button"
            >
              {p.name} • {p.breed || p.species || "Pet"}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
