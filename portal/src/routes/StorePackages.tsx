import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  buyPortalPackage,
  fetchPortalStorePackages,
  type PortalPackageType,
  type PortalPurchaseResponse,
} from '../lib/portal';
import { STORE_BALANCES_QUERY_KEY, STORE_PACKAGES_QUERY_KEY } from '../lib/storeQueries';

const StorePackages = () => {
  const queryClient = useQueryClient();
  const { data, isLoading, isError } = useQuery({
    queryKey: STORE_PACKAGES_QUERY_KEY,
    queryFn: fetchPortalStorePackages,
  });

  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const purchaseMutation = useMutation({
    mutationFn: (pkg: PortalPackageType) =>
      buyPortalPackage({ packageTypeId: pkg.package_type_id, quantity: 1 }),
    onSuccess: (response: PortalPurchaseResponse, pkg) => {
      setMessage(
        `Created invoice ${response.invoice_id.slice(0, 8)} for ${pkg.name}. ` +
          'You can complete payment from the Invoices page whenever you are ready.',
      );
      setError(null);
      queryClient.invalidateQueries({ queryKey: STORE_PACKAGES_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: STORE_BALANCES_QUERY_KEY });
    },
    onError: () => {
      setError('Unable to create the package invoice. Please try again.');
      setMessage(null);
    },
  });

  if (isLoading) {
    return <p className="text-sm text-slate-500">Loading packages…</p>;
  }

  if (isError || !data) {
    return <p className="text-sm text-red-600">Packages are unavailable right now.</p>;
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold text-slate-900">Available packages</h3>
        <p className="text-sm text-slate-500">Remaining credits update automatically after purchase and use.</p>
      </div>
      {message && <p className="rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700">{message}</p>}
      {error && <p className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">{error}</p>}
      {data.length === 0 ? (
        <p className="text-sm text-slate-500">No packages are currently available.</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {data.map((pkg) => (
            <article key={pkg.package_type_id} className="space-y-3 rounded-2xl border border-slate-200 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-base font-semibold text-slate-900">{pkg.name}</h4>
                  <p className="text-xs uppercase tracking-wide text-slate-400">{pkg.applies_to}</p>
                </div>
                <div className="text-right text-sm text-slate-500">
                  <p className="font-medium text-slate-900">Remaining: {pkg.remaining}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => purchaseMutation.mutate(pkg)}
                disabled={purchaseMutation.isPending}
                className="w-full rounded-lg bg-orange-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-orange-600 disabled:cursor-not-allowed disabled:bg-orange-300"
              >
                {purchaseMutation.isPending ? 'Creating invoice…' : 'Buy package'}
              </button>
            </article>
          ))}
        </div>
      )}
    </div>
  );
};

export default StorePackages;
