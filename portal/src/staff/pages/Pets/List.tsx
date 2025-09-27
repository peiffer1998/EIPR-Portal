import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { listPets } from "../../lib/fetchers";

export default function PetsList() {
  const [q, setQ] = useState("");
  const pets = useQuery({ queryKey: ["pets", q], queryFn: () => listPets(undefined, q) });

  return (
    <div className="bg-white p-6 rounded-xl shadow">
      <div className="mb-3 grid gap-1">
        <label className="text-sm text-slate-600">Search</label>
        <input
          className="border rounded px-3 py-2"
          value={q}
          onChange={(event) => setQ(event.target.value)}
          placeholder="pet name"
        />
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-slate-500">
            <th>Pet</th>
            <th>Breed/Species</th>
          </tr>
        </thead>
        <tbody>
          {(pets.data || []).map((p: any) => (
            <tr key={p.id} className="border-t hover:bg-slate-50">
              <td className="py-2">
                <Link to={`/staff/pets/${p.id}`} className="text-blue-700">
                  {p.name}
                </Link>
              </td>
              <td>{p.breed || p.species}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
