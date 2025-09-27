import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import Page from '../../../ui/Page';
import Loading from '../../../ui/Loading';
import Table from '../../../ui/Table';
import { Card, CardHeader } from '../../../ui/Card';
import { myPets } from '../../lib/fetchers';
import type { OwnerPet } from '../../types';

const OwnerPets = (): JSX.Element => {
  const petsQuery = useQuery({ queryKey: ['owner', 'pets'], queryFn: myPets });

  if (petsQuery.isLoading) {
    return <Loading text="Loading pets…" />;
  }

  if (petsQuery.isError) {
    return (
      <Page>
        <Page.Header title="Pets" />
        <Card>
          <CardHeader title="Unable to load pets" sub="Please refresh or try again later." />
        </Card>
      </Page>
    );
  }

  const pets = petsQuery.data ?? [];

  return (
    <Page>
      <Page.Header
        title="My pets"
        sub="View details, update profiles, and upload vaccination documents."
      />
      <Card className="p-0 overflow-hidden">
        <CardHeader title="Pet list" sub={`Total pets: ${pets.length}`} />
        <div className="overflow-x-auto">
          <Table>
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2">Breed</th>
                <th className="px-3 py-2">Species</th>
                <th className="px-3 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {pets.length ? (
                pets.map((pet: OwnerPet) => (
                  <tr key={pet.id} className="border-t border-slate-100 text-sm">
                    <td className="px-3 py-2 font-medium text-slate-800">{pet.name ?? 'Pet'}</td>
                    <td className="px-3 py-2">{pet.breed ?? pet.pet_type ?? '—'}</td>
                    <td className="px-3 py-2">{pet.species ?? '—'}</td>
                    <td className="px-3 py-2">
                      <Link className="text-sm font-medium text-orange-600" to={`/owner/pets/${pet.id}`}>
                        View & edit
                      </Link>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="px-3 py-6 text-center text-sm text-slate-500">
                    You have not added pets yet. Once your pets are on file, they will show up here.
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

export default OwnerPets;
