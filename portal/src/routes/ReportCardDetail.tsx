import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { fetchReportCardDetail } from '../lib/portal';
import LazyImg from '../ui/LazyImg';

const REPORT_CARD_DETAIL_QUERY_KEY = ['portal', 'report-card'];

const ReportCardDetail = () => {
  const { cardId } = useParams();
  const { data, isLoading, isError } = useQuery({
    queryKey: [...REPORT_CARD_DETAIL_QUERY_KEY, cardId],
    queryFn: () => fetchReportCardDetail(cardId ?? ''),
    enabled: Boolean(cardId),
  });

  if (isLoading) {
    return <p className="text-slate-500">Loading report card…</p>;
  }

  if (isError || !data) {
    return (
      <section className="space-y-4">
        <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">
          We couldn't find that report card. It may have been archived.
        </p>
        <Link
          to="/report-cards"
          className="inline-flex items-center gap-2 rounded-full bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600"
        >
          ← Back to report cards
        </Link>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-400">
            {new Date(data.occurred_on).toLocaleDateString()}
          </p>
          <h2 className="text-3xl font-semibold text-slate-900">
            {data.title || `${data.pet_name ?? 'Your pet'}'s report card`}
          </h2>
          {data.summary && <p className="mt-2 text-slate-600">{data.summary}</p>}
          {data.rating !== null && (
            <p className="mt-1 text-sm font-medium text-orange-600">Overall rating: {data.rating} / 5</p>
          )}
        </div>
        <Link
          to="/report-cards"
          className="rounded-full bg-slate-100 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-200"
        >
          Back
        </Link>
      </div>

      {data.media.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-lg font-semibold text-slate-900">Highlights</h3>
          <div className="flex flex-wrap gap-4">
            {data.media.map((item) => (
              <figure key={item.id} className="max-w-xs">
                {item.display_url ? (
                  <LazyImg
                    src={item.display_url}
                    alt={item.document.file_name}
                    className="w-full rounded-xl object-cover shadow-sm"
                  />
                ) : (
                  <div className="flex h-40 items-center justify-center rounded-xl border border-dashed border-slate-300 text-sm text-slate-400">
                    No preview available
                  </div>
                )}
                <figcaption className="mt-2 text-xs text-slate-500">
                  {item.document.file_name}
                </figcaption>
              </figure>
            ))}
          </div>
        </div>
      )}

      {data.friends.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-lg font-semibold text-slate-900">Playmates</h3>
          <ul className="flex flex-wrap gap-2 text-sm text-slate-600">
            {data.friends.map((friend) => (
              <li key={friend.id} className="rounded-full bg-slate-100 px-3 py-1">
                {friend.name}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="rounded-2xl bg-slate-50 px-6 py-4 text-sm text-slate-500">
        <p>
          Questions or need additional updates? Call our front desk and reference report card
          <span className="font-semibold"> #{data.id.slice(0, 8)}</span>.
        </p>
      </div>
    </section>
  );
};

export default ReportCardDetail;
