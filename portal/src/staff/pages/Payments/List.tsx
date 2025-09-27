import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import Money from "../../components/Money";
import { listPayments } from "../../lib/billingFetchers";

export default function PaymentsList() {
  const [from, setFrom] = useState<string>(new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10));
  const [to, setTo] = useState<string>(new Date().toISOString().slice(0, 10));
  const [provider, setProvider] = useState<string>("");

  const paymentsQuery = useQuery({
    queryKey: ["payments", from, to, provider],
    queryFn: () =>
      listPayments({
        date_from: from,
        date_to: to,
        provider: provider || undefined,
        limit: 200,
      }),
  });

  const payments = paymentsQuery.data ?? [];

  return (
    <div className="grid gap-4">
      <div className="grid gap-3 rounded-xl bg-white p-4 shadow md:grid-cols-4">
        <label className="text-sm">
          <span className="text-slate-600">From</span>
          <input type="date" className="mt-1 w-full rounded border px-3 py-2" value={from} onChange={(event) => setFrom(event.target.value)} />
        </label>
        <label className="text-sm">
          <span className="text-slate-600">To</span>
          <input type="date" className="mt-1 w-full rounded border px-3 py-2" value={to} onChange={(event) => setTo(event.target.value)} />
        </label>
        <label className="text-sm md:col-span-2">
          <span className="text-slate-600">Provider</span>
          <input
            className="mt-1 w-full rounded border px-3 py-2"
            placeholder="stripe, cash, check…"
            value={provider}
            onChange={(event) => setProvider(event.target.value)}
          />
        </label>
      </div>

      <div className="overflow-auto rounded-xl bg-white shadow">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500">
              <th className="px-3 py-2">Payment</th>
              <th className="px-3 py-2">Provider</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Amount</th>
              <th className="px-3 py-2">Invoice</th>
            </tr>
          </thead>
          <tbody>
            {payments.map((payment: any) => (
              <tr key={payment.id} className="border-t hover:bg-slate-50">
                <td className="px-3 py-2">{payment.id}</td>
                <td className="px-3 py-2">{payment.provider || ""}</td>
                <td className="px-3 py-2">{payment.status || ""}</td>
                <td className="px-3 py-2">
                  <Money value={payment.amount ?? 0} />
                </td>
                <td className="px-3 py-2">{payment.invoice_id || ""}</td>
              </tr>
            ))}
            {payments.length === 0 && (
              <tr>
                <td className="px-3 py-4 text-sm text-slate-500" colSpan={5}>
                  {paymentsQuery.isLoading ? "Loading…" : "No payments found for the selected filters."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
