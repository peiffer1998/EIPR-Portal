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
          {(owners.data || []).map((o: any) => {
            const user = o.user ?? {};
            const fullName = [user.first_name, user.last_name].filter(Boolean).join(" ") || "—";
            const email = user.email ?? o.email ?? "—";
            const phone = user.phone_number ?? o.phone ?? "—";
            return (
              <tr key={o.id} className="border-t hover:bg-slate-50">
                <td className="py-2">
                  <Link to={`/staff/customers/${o.id}`} className="text-blue-700">
                    {fullName}
                  </Link>
                </td>
                <td>{email}</td>
                <td>{phone}</td>
              </tr>
            );
          })}
          {owners.isSuccess && !owners.data?.length ? (
            <tr className="border-t">
              <td colSpan={3} className="py-6 text-center text-slate-400">
                No customers found.
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
