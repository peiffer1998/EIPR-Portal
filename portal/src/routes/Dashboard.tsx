import { useEffect } from 'react';

import { usePortalMe } from '../lib/usePortalMe';
import { useAuth } from '../state/AuthContext';

const Dashboard = () => {
  const { data, isLoading } = usePortalMe();
  const { setOwner } = useAuth();

  useEffect(() => {
    if (data?.owner) {
      setOwner({
        id: data.owner.id,
        firstName: data.owner.user.first_name,
        lastName: data.owner.user.last_name,
        email: data.owner.user.email,
      });
    }
  }, [data, setOwner]);

  if (isLoading) {
    return <p className="text-slate-500">Loading your portal…</p>;
  }

  const pets = data?.pets ?? [];
  const upcoming = data?.upcoming_reservations ?? [];
  const unpaid = data?.unpaid_invoices ?? [];

  return (
    <section className="grid gap-6 md:grid-cols-3">
      <div className="rounded-2xl bg-white p-6 shadow-sm">
        <p className="text-sm uppercase text-slate-400">Pets</p>
        <p className="mt-2 text-4xl font-semibold text-slate-900">{pets.length}</p>
        <p className="mt-1 text-sm text-slate-500">Registered companions</p>
      </div>
      <div className="rounded-2xl bg-white p-6 shadow-sm">
        <p className="text-sm uppercase text-slate-400">Upcoming stays</p>
        <p className="mt-2 text-4xl font-semibold text-slate-900">{upcoming.length}</p>
        <p className="mt-1 text-sm text-slate-500">Requests and confirmed visits</p>
      </div>
      <div className="rounded-2xl bg-white p-6 shadow-sm">
        <p className="text-sm uppercase text-slate-400">Unpaid invoices</p>
        <p className="mt-2 text-4xl font-semibold text-slate-900">{unpaid.length}</p>
        <p className="mt-1 text-sm text-slate-500">Settle balances before drop-off</p>
      </div>
    </section>
  );
};

export default Dashboard;
