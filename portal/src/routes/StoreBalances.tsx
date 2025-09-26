import { useQuery } from '@tanstack/react-query';

import { fetchPortalStoreBalances } from '../lib/portal';
import { STORE_BALANCES_QUERY_KEY } from '../lib/storeQueries';

const StoreBalances = () => {
  const { data, isLoading, isError } = useQuery({
    queryKey: STORE_BALANCES_QUERY_KEY,
    queryFn: fetchPortalStoreBalances,
  });

  if (isLoading) {
    return <p className="text-sm text-slate-500">Loading balances…</p>;
  }

  if (isError || !data) {
    return <p className="text-sm text-red-600">Unable to load balances right now.</p>;
  }

  return (
    <div className="space-y-4">
      <section>
        <h3 className="text-lg font-semibold text-slate-900">Package credits</h3>
        {data.packages.length === 0 ? (
          <p className="text-sm text-slate-500">No package credits yet.</p>
        ) : (
          <ul className="mt-3 space-y-2 text-sm text-slate-600">
            {data.packages.map((pkg) => (
              <li key={pkg.package_type_id} className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2">
                <span className="font-medium text-slate-900">{pkg.name}</span>
                <span className="text-slate-500">Remaining: {pkg.remaining}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h3 className="text-lg font-semibold text-slate-900">Store credit</h3>
        <p className="text-sm text-slate-600">
          Available balance: <span className="font-semibold text-slate-900">${Number(data.store_credit.balance).toFixed(2)}</span>
        </p>
        <p className="mt-2 text-xs text-slate-500">
          Store credit can be applied to open invoices from the Invoices page.
        </p>
      </section>
    </div>
  );
};

export default StoreBalances;
