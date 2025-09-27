import { useMemo, useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { LogOut, Menu, X } from 'lucide-react';

import SkipToContent from '../../a11y/SkipToContent';
import Button from '../../ui/Button';
import { useAuth } from '../../state/useAuth';

const NAV_LINKS: Array<{ to: string; label: string; end?: boolean }> = [
  { to: '/owner', label: 'Dashboard', end: true },
  { to: '/owner/pets', label: 'Pets' },
  { to: '/owner/reservations', label: 'Reservations' },
  { to: '/owner/grooming', label: 'Grooming' },
  { to: '/owner/packages', label: 'Packages' },
  { to: '/owner/credits', label: 'Credits' },
  { to: '/owner/invoices', label: 'Invoices' },
  { to: '/owner/report-cards', label: 'Report Cards' },
  { to: '/owner/documents', label: 'Documents' },
  { to: '/owner/preferences', label: 'Preferences' },
];

const OwnerShell = (): JSX.Element => {
  const { owner, logout } = useAuth();
  const [navOpen, setNavOpen] = useState(false);

  const initials = useMemo(() => {
    const first = owner?.firstName?.[0] ?? '';
    const last = owner?.lastName?.[0] ?? '';
    return (first + last).toUpperCase();
  }, [owner?.firstName, owner?.lastName]);

  return (
    <div className="min-h-screen bg-slate-100">
      <SkipToContent targetId="owner-main" />
      <header className="bg-white shadow-sm">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <Button
              className="sm:hidden border border-slate-200 shadow-sm"
              variant="ghost"
              onClick={() => setNavOpen((open) => !open)}
              aria-expanded={navOpen}
              aria-label="Toggle navigation"
              type="button"
            >
              {navOpen ? <X size={18} /> : <Menu size={18} />}
            </Button>
            <div>
              <div className="text-lg font-semibold text-slate-900">Owner Portal</div>
              {owner ? (
                <div className="text-sm text-slate-500">Welcome back, {owner?.firstName}</div>
              ) : null}
            </div>
          </div>
          <div className="flex items-center gap-3">
            {owner ? (
              <div className="flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-600">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-orange-500 text-white">
                  {initials || owner?.email?.[0]?.toUpperCase() || 'O'}
                </div>
                <div className="hidden sm:flex flex-col leading-tight">
                  <span className="font-medium text-slate-800">{owner?.firstName} {owner?.lastName}</span>
                  <span className="text-xs text-slate-500">{owner?.email}</span>
                </div>
              </div>
            ) : null}
            <Button
              className="inline-flex items-center gap-2"
              variant="secondary"
              onClick={logout}
              type="button"
            >
              <LogOut size={16} />
              Sign out
            </Button>
          </div>
        </div>
        <nav className="border-t border-slate-200 bg-white">
          <div className="mx-auto hidden max-w-6xl flex-wrap items-center gap-2 px-4 py-2 sm:flex sm:px-6">
            {NAV_LINKS.map(({ to, label, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  `rounded-full px-3 py-1 text-sm font-medium transition ${
                    isActive ? 'bg-orange-500 text-white shadow-sm' : 'text-slate-500 hover:text-slate-900'
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </div>
        </nav>
      </header>
      {navOpen ? (
        <div className="border-b border-slate-200 bg-white px-4 py-3 sm:hidden">
          <div className="flex flex-col gap-2">
            {NAV_LINKS.map(({ to, label, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                onClick={() => setNavOpen(false)}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-2 text-sm transition ${
                    isActive ? 'bg-orange-500 text-white' : 'text-slate-600 hover:bg-slate-100'
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </div>
        </div>
      ) : null}
      <main id="owner-main" tabIndex={-1} className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <Outlet />
      </main>
    </div>
  );
};

export default OwnerShell;
