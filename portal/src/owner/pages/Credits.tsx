import { useQuery } from '@tanstack/react-query';

import Page from '../../ui/Page';
import Loading from '../../ui/Loading';
import Table from '../../ui/Table';
import { Card, CardHeader } from '../../ui/Card';
import { fmtDateTime } from '../../lib/datetime';
import { myCredit } from '../lib/fetchers';
import { formatCurrency } from '../lib/format';
import type { OwnerCreditLedgerEntry } from '../types';

const OwnerCredits = (): JSX.Element => {
  const creditQuery = useQuery({ queryKey: ['owner', 'credit'], queryFn: myCredit });

  if (creditQuery.isLoading) {
    return <Loading text="Loading store credit…" />;
  }

  if (creditQuery.isError) {
    return (
      <Page>
        <Page.Header title="Store credit" />
        <Card>
          <CardHeader title="Unable to load store credit" sub="Please refresh or contact the resort." />
        </Card>
      </Page>
    );
  }

  const credit = creditQuery.data;
  const ledger = credit?.ledger ?? [];

  return (
    <Page>
      <Page.Header title="Store credit" sub="Track credit balance and adjustments." />
      <div className="grid gap-3 md:grid-cols-[1fr_2fr]">
        <Card className="p-4">
          <CardHeader title="Current balance" />
          <div className="text-4xl font-semibold text-slate-900">
            {formatCurrency(credit?.balance ?? 0)}
          </div>
        </Card>
        <Card className="p-0 overflow-hidden md:col-span-1 md:row-span-2">
          <CardHeader title="Ledger" sub={`${ledger.length} entries`} />
          <div className="overflow-x-auto">
            <Table>
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-3 py-2">Date</th>
                  <th className="px-3 py-2">Type</th>
                  <th className="px-3 py-2">Amount</th>
                  <th className="px-3 py-2">Note</th>
                </tr>
              </thead>
              <tbody>
                {ledger.length ? (
                  ledger.map((entry: OwnerCreditLedgerEntry, index) => (
                    <tr key={entry.id ?? index} className="border-t border-slate-100 text-sm">
                      <td className="px-3 py-2">
                        {entry.ts ? fmtDateTime(entry.ts) : entry.date ? fmtDateTime(entry.date) : '—'}
                      </td>
                      <td className="px-3 py-2 uppercase">{entry.type ?? 'Entry'}</td>
                      <td className="px-3 py-2">{formatCurrency(entry.amount ?? 0)}</td>
                      <td className="px-3 py-2 text-slate-600">{entry.note ?? '—'}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} className="px-3 py-6 text-center text-sm text-slate-500">
                      No credit activity yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </Table>
          </div>
        </Card>
      </div>
    </Page>
  );
};

export default OwnerCredits;
