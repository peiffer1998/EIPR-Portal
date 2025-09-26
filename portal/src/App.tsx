import { NavLink, Outlet } from 'react-router-dom';

import { useAuth } from './state/useAuth';

const navLinks = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/pets', label: 'Pets' },
  { to: '/reservations', label: 'Reservations' },
  { to: '/invoices', label: 'Invoices' },
  { to: '/report-cards', label: 'Report Cards' },
  { to: '/store', label: 'Store' },
  { to: '/uploads', label: 'Uploads' },
];

const App = () => {
  const { owner, logout } = useAuth();

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="bg-white shadow-sm">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">Eastern Iowa Pet Resort</h1>
            {owner && (
              <p className="text-sm text-slate-500">Welcome back, {owner.firstName}</p>
            )}
          </div>
          <button
            type="button"
            onClick={logout}
            className="rounded-full bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600"
          >
            Logout
          </button>
        </div>
        <nav className="border-t border-slate-200 bg-white">
          <div className="mx-auto flex max-w-6xl gap-4 px-6 py-2 text-sm font-medium">
            {navLinks.map(({ to, label, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  `rounded-full px-3 py-1 transition ${isActive ? 'bg-orange-500 text-white' : 'text-slate-500 hover:text-slate-900'}`
                }
              >
                {label}
              </NavLink>
            ))}
          </div>
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-10">
        <Outlet />
      </main>
    </div>
  );
};

export default App;
