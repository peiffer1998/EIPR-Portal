import { useQuery } from '@tanstack/react-query';

import Page from '../../ui/Page';
import Loading from '../../ui/Loading';
import Table from '../../ui/Table';
import { Card, CardHeader } from '../../ui/Card';
import { myPackages } from '../lib/fetchers';
import type { OwnerPackageSummary } from '../types';

const OwnerPackages = (): JSX.Element => {
  const packagesQuery = useQuery({ queryKey: ['owner', 'packages'], queryFn: myPackages });

  if (packagesQuery.isLoading) {
    return <Loading text="Loading packages…" />;
  }

  if (packagesQuery.isError) {
    return (
      <Page>
        <Page.Header title="Packages" />
        <Card>
          <CardHeader title="Unable to load packages" sub="Please refresh or contact the resort." />
        </Card>
      </Page>
    );
  }

  const packages = packagesQuery.data ?? [];

  return (
    <Page>
      <Page.Header title="Packages" sub="Track remaining days, nights, or credits." />
      <Card className="p-0 overflow-hidden">
        <CardHeader title="Active packages" sub={`Total: ${packages.length}`} />
        <div className="overflow-x-auto">
          <Table>
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="px-3 py-2">Package</th>
                <th className="px-3 py-2">Remaining</th>
                <th className="px-3 py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {packages.length ? (
                packages.map((pkg: OwnerPackageSummary) => (
                  <tr key={pkg.id} className="border-t border-slate-100 text-sm">
                    <td className="px-3 py-2">{pkg.package?.name ?? pkg.package_name ?? 'Package'}</td>
                    <td className="px-3 py-2">{pkg.remaining ?? pkg.balance ?? 0}</td>
                    <td className="px-3 py-2">
                      <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-medium uppercase text-slate-600">
                        {pkg.status ?? 'ACTIVE'}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={3} className="px-3 py-6 text-center text-sm text-slate-500">
                    No packages on file yet.
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

export default OwnerPackages;
