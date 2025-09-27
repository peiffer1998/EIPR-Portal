import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { listPets } from "../../lib/fetchers";

export default function PetsList() {
  const [q, setQ] = useState("");
  const pets = useQuery({ queryKey: ["pets", q], queryFn: () => listPets(undefined, q) });
  const rows = pets.data || [];

  return (
    <div className="bg-white p-6 rounded-xl shadow">
      <div className="mb-3 grid gap-1">
        <label className="text-sm text-slate-600">Search</label>
        <input
          className="border rounded px-3 py-2"
          value={q}
          onChange={(event) => setQ(event.target.value)}
          placeholder="pet or owner"
        />
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-slate-500">
            <th className="px-3 py-2">Pet</th>
            <th className="px-3 py-2">Owner</th>
            <th className="px-3 py-2">Breed</th>
            <th className="px-3 py-2">Type</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((p: any) => {
            const owner = p.owner || {};
            const ownerName = [owner.first_name, owner.last_name].filter(Boolean).join(" ") || "—";
            const ownerId = owner.id || p.owner_id;
            const typeLabel = (p.pet_type || p.species || "").replace(/_/g, " ");
            const breed = p.breed || "—";
            return (
              <tr key={p.id} className="border-t hover:bg-slate-50">
                <td className="px-3 py-2">
                  <Link to={`/staff/pets/${p.id}`} className="text-blue-700">
                    {p.name || "—"}
                  </Link>
                </td>
                <td className="px-3 py-2">
                  {ownerId ? (
                    <Link to={`/staff/customers/${ownerId}`} className="text-blue-700">
                      {ownerName}
                    </Link>
                  ) : (
                    ownerName
                  )}
                </td>
                <td className="px-3 py-2">{breed}</td>
                <td className="px-3 py-2 capitalize">{typeLabel || "—"}</td>
              </tr>
            );
          })}
          {pets.isSuccess && !rows.length ? (
            <tr className="border-t">
              <td colSpan={4} className="px-3 py-6 text-center text-slate-400">
                No pets found.
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
