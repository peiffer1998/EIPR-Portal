import { useQuery } from '@tanstack/react-query';

import Page from '../../ui/Page';
import Loading from '../../ui/Loading';
import Table from '../../ui/Table';
import { Card, CardHeader } from '../../ui/Card';
import { fmtDateTime } from '../../lib/datetime';
import { myInvoices } from '../lib/fetchers';
import { formatCurrency } from '../lib/format';
import type { OwnerInvoice } from '../types';

const OwnerInvoices = (): JSX.Element => {
  const invoicesQuery = useQuery({ queryKey: ['owner', 'invoices'], queryFn: myInvoices });

  if (invoicesQuery.isLoading) {
    return <Loading text="Loading invoices…" />;
  }

  if (invoicesQuery.isError) {
    return (
      <Page>
        <Page.Header title="Invoices" />
        <Card>
          <CardHeader title="Unable to load invoices" sub="Please refresh or contact the resort." />
        </Card>
      </Page>
    );
  }

  const invoices = invoicesQuery.data ?? [];

  return (
    <Page>
      <Page.Header title="Invoices" sub="Download receipts and check outstanding balances." />
      <Card className="p-0 overflow-hidden">
        <CardHeader title="Invoice history" sub={`Total: ${invoices.length}`} />
        <div className="overflow-x-auto">
          <Table>
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="px-3 py-2">Invoice</th>
                <th className="px-3 py-2">Pet</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Total</th>
                <th className="px-3 py-2">Created</th>
                <th className="px-3 py-2">Receipt</th>
              </tr>
            </thead>
            <tbody>
              {invoices.length ? (
                invoices.map((invoice: OwnerInvoice) => (
                  <tr key={invoice.id} className="border-t border-slate-100 text-sm">
                    <td className="px-3 py-2 font-medium text-slate-800">{invoice.id}</td>
                    <td className="px-3 py-2">{invoice.pet_name ?? invoice.pet_id ?? '—'}</td>
                    <td className="px-3 py-2">
                      <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold uppercase text-slate-600">
                        {invoice.status ?? 'OPEN'}
                      </span>
                    </td>
                    <td className="px-3 py-2">{formatCurrency(invoice.total ?? 0)}</td>
                    <td className="px-3 py-2">
                      {invoice.created_at ? fmtDateTime(invoice.created_at) : '—'}
                    </td>
                    <td className="px-3 py-2">
                      <a
                        className="text-sm font-medium text-orange-600"
                        href={`/staff/print/receipt/${invoice.id}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open receipt
                      </a>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="px-3 py-6 text-center text-sm text-slate-500">
                    No invoices yet. As you complete services, invoices will appear here.
                  </td>
                </tr>
              )}
            </tbody>
          </Table>
        </div>
      </Card>
    </Page>
  );
};

export default OwnerInvoices;
