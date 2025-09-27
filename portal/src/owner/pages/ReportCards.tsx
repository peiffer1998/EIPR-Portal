import { useQuery } from '@tanstack/react-query';

import Page from '../../ui/Page';
import Loading from '../../ui/Loading';
import Table from '../../ui/Table';
import { Card, CardHeader } from '../../ui/Card';
import { fmtDate } from '../../lib/datetime';
import { myReportCards } from '../lib/fetchers';
import type { OwnerReportCard } from '../types';

const OwnerReportCards = (): JSX.Element => {
  const reportCardsQuery = useQuery({ queryKey: ['owner', 'report-cards'], queryFn: myReportCards });

  if (reportCardsQuery.isLoading) {
    return <Loading text="Loading report cards…" />;
  }

  if (reportCardsQuery.isError) {
    return (
      <Page>
        <Page.Header title="Report cards" />
        <Card>
          <CardHeader title="Unable to load report cards" sub="Please refresh or contact the resort." />
        </Card>
      </Page>
    );
  }

  const cards = reportCardsQuery.data ?? [];

  return (
    <Page>
      <Page.Header title="Report cards" sub="Daily updates, friends, and photos from recent stays." />
      <Card className="p-0 overflow-hidden">
        <CardHeader title="History" sub={`Total: ${cards.length}`} />
        <div className="overflow-x-auto">
          <Table>
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="px-3 py-2">Pet</th>
                <th className="px-3 py-2">Date</th>
                <th className="px-3 py-2">Summary</th>
                <th className="px-3 py-2">Media</th>
              </tr>
            </thead>
            <tbody>
              {cards.length ? (
                cards.map((card: OwnerReportCard) => (
                  <tr key={card.id} className="border-t border-slate-100 text-sm">
                    <td className="px-3 py-2 font-medium text-slate-800">{card.pet?.name ?? card.pet_name ?? 'Pet'}</td>
                    <td className="px-3 py-2">{card.occurred_on ? fmtDate(card.occurred_on) : '—'}</td>
                    <td className="px-3 py-2 text-slate-600">{card.summary ?? card.notes ?? '—'}</td>
                    <td className="px-3 py-2">{card.media?.length ?? 0}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="px-3 py-6 text-center text-sm text-slate-500">
                    No report cards yet. After your next visit you can review them here.
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

export default OwnerReportCards;
