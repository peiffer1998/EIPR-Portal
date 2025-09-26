import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { fetchReportCards } from '../lib/portal';
import { usePortalMe } from '../lib/usePortalMe';

const REPORT_CARDS_QUERY_KEY = ['portal', 'report-cards'];

const ReportCards = () => {
  const { data: me, isLoading: loadingProfile } = usePortalMe();
  const pets = useMemo(() => me?.pets ?? [], [me?.pets]);
  const [petFilter, setPetFilter] = useState<string>('all');

  const { data, isLoading } = useQuery({
    queryKey: [...REPORT_CARDS_QUERY_KEY, petFilter],
    queryFn: () => fetchReportCards(petFilter === 'all' ? undefined : petFilter),
  });

  const cards = data ?? [];

  if (loadingProfile || isLoading) {
    return <p className="text-slate-500">Loading report cards…</p>;
  }

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-slate-900">Report Cards</h2>
          <p className="text-sm text-slate-500">Browse daily updates from your pet's stays.</p>
        </div>
        {pets.length > 1 && (
          <label className="flex items-center gap-2 text-sm text-slate-600">
            Show for
            <select
              value={petFilter}
              onChange={(event) => setPetFilter(event.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:border-orange-500 focus:outline-none"
            >
              <option value="all">All pets</option>
              {pets.map((pet) => (
                <option key={pet.id} value={pet.id}>
                  {pet.name}
                </option>
              ))}
            </select>
          </label>
        )}
      </header>

      {cards.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-10 text-center text-slate-500">
          <p>No report cards available yet. We'll email you as soon as one is ready.</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {cards.map((card) => (
            <article
              key={card.id}
              className="flex h-full flex-col justify-between rounded-2xl bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-400">
                  <span>{new Date(card.occurred_on).toLocaleDateString()}</span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                      card.status === 'sent' ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-600'
                    }`}
                  >
                    {card.status}
                  </span>
                </div>
                <h3 className="text-lg font-semibold text-slate-900">{card.title || `${card.pet_name ?? 'Your pet'}'s day`}</h3>
                {card.summary && <p className="text-sm text-slate-600">{card.summary}</p>}
                {card.rating !== null && (
                  <p className="text-sm text-orange-600">Rating: {card.rating} / 5</p>
                )}
              </div>
              <div className="mt-4 flex items-center justify-between text-sm text-slate-500">
                <span>{card.pet_name}</span>
                <Link
                  to={`/report-cards/${card.id}`}
                  className="inline-flex items-center gap-1 rounded-full bg-orange-500 px-3 py-1 text-xs font-medium text-white hover:bg-orange-600"
                >
                  View details
                </Link>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
};

export default ReportCards;
