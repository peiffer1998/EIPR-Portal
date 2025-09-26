import { NavLink, Outlet } from 'react-router-dom';

const tabs = [
  { to: '/store', label: 'Packages', end: true },
  { to: '/store/gift-certificates', label: 'Gift Certificates' },
  { to: '/store/balances', label: 'Balances' },
];

const Store = () => (
  <section className="space-y-6">
    <header className="space-y-2">
      <h2 className="text-2xl font-semibold text-slate-900">Store</h2>
      <p className="text-sm text-slate-500">
        Purchase daycare or boarding packages, send gift certificates, and keep track of your remaining credits.
      </p>
    </header>
    <nav className="flex gap-3">
      {tabs.map(({ to, label, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            `rounded-full px-3 py-1 text-sm font-medium transition ${isActive ? 'bg-orange-500 text-white' : 'text-slate-500 hover:text-slate-900'}`
          }
        >
          {label}
        </NavLink>
      ))}
    </nav>
    <div className="rounded-2xl bg-white p-6 shadow-sm">
      <Outlet />
    </div>
  </section>
);

export default Store;
