import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import Money from "../../components/Money";
import { listInvoices } from "../../lib/billingFetchers";

export default function InvoicesList() {
  const [from, setFrom] = useState<string>(new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10));
  const [to, setTo] = useState<string>(new Date().toISOString().slice(0, 10));
  const [status, setStatus] = useState<string>("");
  const [search, setSearch] = useState<string>("");

  const invoicesQuery = useQuery({
    queryKey: ["invoices", from, to, status, search],
    queryFn: () =>
      listInvoices({
        date_from: from,
        date_to: to,
        status: status || undefined,
        q: search || undefined,
        limit: 200,
      }),
  });

  const invoices = invoicesQuery.data ?? [];

  return (
    <div className="grid gap-4">
      <div className="grid gap-3 rounded-xl bg-white p-4 shadow md:grid-cols-5">
        <label className="text-sm">
          <span className="text-slate-600">From</span>
          <input type="date" className="mt-1 w-full rounded border px-3 py-2" value={from} onChange={(event) => setFrom(event.target.value)} />
        </label>
        <label className="text-sm">
          <span className="text-slate-600">To</span>
          <input type="date" className="mt-1 w-full rounded border px-3 py-2" value={to} onChange={(event) => setTo(event.target.value)} />
        </label>
        <label className="text-sm">
          <span className="text-slate-600">Status</span>
          <select className="mt-1 w-full rounded border px-3 py-2" value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">Any</option>
            <option value="PENDING">Pending</option>
            <option value="PAID">Paid</option>
            <option value="REFUNDED">Refunded</option>
          </select>
        </label>
        <label className="text-sm md:col-span-2">
          <span className="text-slate-600">Search</span>
          <input
            className="mt-1 w-full rounded border px-3 py-2"
            placeholder="Owner, pet, invoice #"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
      </div>

      <div className="overflow-auto rounded-xl bg-white shadow">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500">
              <th className="px-3 py-2">Invoice</th>
              <th className="px-3 py-2">Owner</th>
              <th className="px-3 py-2">Pet</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Total</th>
            </tr>
          </thead>
          <tbody>
            {invoices.map((invoice: any) => (
              <tr key={invoice.id} className="border-t hover:bg-slate-50">
                <td className="px-3 py-2">
                  <Link className="text-blue-700" to={`/staff/invoices/${invoice.id}`}>
                    {invoice.id}
                  </Link>
                </td>
                <td className="px-3 py-2">{invoice.owner_name || invoice.owner_id || ""}</td>
                <td className="px-3 py-2">{invoice.pet_name || invoice.pet_id || ""}</td>
                <td className="px-3 py-2">{invoice.status}</td>
                <td className="px-3 py-2">
                  <Money value={invoice.total ?? 0} />
                </td>
              </tr>
            ))}
            {invoices.length === 0 && (
              <tr>
                <td className="px-3 py-4 text-sm text-slate-500" colSpan={5}>
                  {invoicesQuery.isLoading ? "Loading…" : "No invoices found for the selected filters."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
