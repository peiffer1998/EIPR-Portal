import { usePortalMe } from '../lib/usePortalMe';

const Pets = () => {
  const { data, isLoading } = usePortalMe();

  if (isLoading) {
    return <p className="text-slate-500">Loading pets…</p>;
  }

  const pets = data?.pets ?? [];

  if (pets.length === 0) {
    return <p className="text-slate-500">No pets on file yet. Add one with the front desk team.</p>;
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {pets.map((pet) => (
        <div key={pet.id} className="rounded-2xl bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-semibold text-slate-900">{pet.name}</h3>
              <p className="text-sm uppercase text-slate-400">{pet.pet_type}</p>
            </div>
          </div>
          <div className="mt-4 space-y-2">
            {(pet.immunization_records ?? []).length === 0 ? (
              <p className="text-sm text-slate-500">No immunizations uploaded yet.</p>
            ) : (
              pet.immunization_records.map((record) => (
                <div key={record.id} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2">
                  <div>
                    <p className="text-sm font-medium text-slate-700">
                      {record.immunization_type?.name ?? 'Vaccination'}
                    </p>
                    <p className="text-xs text-slate-400">Status: {record.status}</p>
                  </div>
                  {record.expires_on && (
                    <span className="text-xs text-slate-500">Expires {new Date(record.expires_on).toLocaleDateString()}</span>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

export default Pets;
