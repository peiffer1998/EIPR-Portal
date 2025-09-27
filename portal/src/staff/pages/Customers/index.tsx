import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { listOwners } from "../../lib/fetchers";

export default function CustomersList() {
  const [q, setQ] = useState("");
  const owners = useQuery({ queryKey: ["owners", q], queryFn: () => listOwners(q) });

  return (
    <div className="bg-white p-6 rounded-xl shadow">
      <div className="mb-3 grid gap-1">
        <label className="text-sm text-slate-600">Search</label>
        <input
          className="border rounded px-3 py-2"
          value={q}
          onChange={(event) => setQ(event.target.value)}
          placeholder="name, email, phone"
        />
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-slate-500">
            <th>Name</th>
            <th>Email</th>
            <th>Phone</th>
          </tr>
        </thead>
        <tbody>
          {(owners.data || []).map((o: any) => (
            <tr key={o.id} className="border-t hover:bg-slate-50">
              <td className="py-2">
                <Link to={`/staff/customers/${o.id}`} className="text-blue-700">
                  {o.first_name} {o.last_name}
                </Link>
              </td>
              <td>{o.email}</td>
              <td>{o.phone}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
