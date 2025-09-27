import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import Button from "../../../ui/Button";
import { Card } from "../../../ui/Card";
import Page from "../../../ui/Page";
import Table from "../../../ui/Table";
import { Input, Label, Select } from "../../../ui/Inputs";
import Money from "../../components/Money";
import { listInvoices } from "../../lib/billingFetchers";

export default function InvoicesList() {
  const [from, setFrom] = useState<string>(new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10));
  const [to, setTo] = useState<string>(new Date().toISOString().slice(0, 10));
  const [status, setStatus] = useState<string>("");
  const [search, setSearch] = useState<string>("");
  const [page, setPage] = useState<number>(0);
  const pageSize = 50;

  useEffect(() => {
    setPage(0);
  }, [from, to, status, search]);

  const invoicesQuery = useQuery({
    queryKey: ["invoices", from, to, status, search, page, pageSize],
    queryFn: () =>
      listInvoices({
        date_from: from,
        date_to: to,
        status: status || undefined,
        q: search || undefined,
        limit: pageSize,
        offset: page * pageSize,
      }),
    keepPreviousData: true,
  });

  const invoices = invoicesQuery.data?.items ?? [];
  const total = invoicesQuery.data?.total ?? 0;
  const currentOffset = invoicesQuery.data?.offset ?? page * pageSize;
  const showingStart = invoices.length ? currentOffset + 1 : 0;
  const showingEnd = invoices.length ? currentOffset + invoices.length : 0;
  const canPrev = page > 0 && !invoicesQuery.isFetching;
  const canNext = currentOffset + invoices.length < total && !invoicesQuery.isFetching;

  return (
    <Page>
      <Page.Header
        title="Invoices"
        actions={
          <Button type="button" variant="ghost" onClick={() => invoicesQuery.refetch()}>
            Refresh
          </Button>
        }
      />

      <Card>
        <div className="grid gap-3 md:grid-cols-5">
          <Label>
            <span className="text-slate-600">From</span>
            <Input type="date" value={from} onChange={(event) => setFrom(event.target.value)} />
          </Label>
          <Label>
            <span className="text-slate-600">To</span>
            <Input type="date" value={to} onChange={(event) => setTo(event.target.value)} />
          </Label>
          <Label>
            <span className="text-slate-600">Status</span>
            <Select value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="">Any</option>
              <option value="PENDING">Pending</option>
              <option value="PAID">Paid</option>
              <option value="REFUNDED">Refunded</option>
            </Select>
          </Label>
          <Label className="md:col-span-2">
            <span className="text-slate-600">Search</span>
            <Input
              placeholder="Owner, pet, invoice #"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </Label>
        </div>
      </Card>

      <Card className="overflow-auto">
        <div className="flex items-center justify-between px-3 py-2 text-sm text-slate-600">
          <span>
            {total
              ? `Showing ${showingStart}-${showingEnd} of ${total}`
              : invoicesQuery.isLoading
                ? "Loading…"
                : "No invoices found"}
          </span>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="ghost"
              disabled={!canPrev}
              onClick={() => setPage((prev) => Math.max(0, prev - 1))}
            >
              Previous
            </Button>
            <Button
              type="button"
              variant="ghost"
              disabled={!canNext}
              onClick={() => setPage((prev) => prev + 1)}
            >
              Next
            </Button>
          </div>
        </div>
        <Table>
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
        </Table>
      </Card>
    </Page>
  );
}
