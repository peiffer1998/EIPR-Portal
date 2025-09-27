import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { LogOut } from "lucide-react";

import StaffSearchBar from "./StaffSearchBar";
import { useStaffAuth } from "../state/StaffAuthContext";
import SkipToContent from "../../a11y/SkipToContent";
import QuickSearch from "../../ui/QuickSearch";
import { attachPrefetch } from "../../perf/prefetch";

const PREFETCH_IMPORTERS: Record<string, () => Promise<unknown>> = {
  "/staff/grooming/board": () => import("../pages/Grooming/Board"),
  "/staff/daycare/roster": () => import("../pages/Daycare/Roster"),
  "/staff/invoices": () => import("../pages/Invoices/List"),
  "/staff/reports": () => import("../pages/Reports"),
};

const PREFETCH_KEYS = new Set(Object.keys(PREFETCH_IMPORTERS));

const groups: {
  title: string;
  links: { to: string; label: string; end?: boolean }[];
}[] = [
  { title: "Overview", links: [{ to: "/staff", label: "Dashboard", end: true }] },
  {
    title: "Calendar",
    links: [
      { to: "/staff/calendar/boarding", label: "Boarding" },
      { to: "/staff/calendar/daycare", label: "Daycare" },
      { to: "/staff/calendar/grooming", label: "Grooming" },
      { to: "/staff/calendar/combined", label: "Combined" },
    ],
  },
  {
    title: "Reservations & Grooming",
    links: [
      { to: "/staff/reservations", label: "Reservations" },
      { to: "/staff/reservations/new", label: "New Reservation" },
      { to: "/staff/grooming/new", label: "New Groom" },
      { to: "/staff/waitlist", label: "Waitlist" },
      { to: "/staff/precheck", label: "Pre-check" },
    ],
  },
  {
    title: "Customers & Pets",
    links: [
      { to: "/staff/customers", label: "Customers" },
      { to: "/staff/pets/list", label: "Pets" },
    ],
  },
  {
    title: "Ops Boards",
    links: [
      { to: "/staff/boarding/feeding", label: "Feeding" },
      { to: "/staff/boarding/meds", label: "Meds" },
      { to: "/staff/boarding/belongings", label: "Belongings" },
      { to: "/staff/daycare/roster", label: "Daycare Roster" },
      { to: "/staff/ops/incidents", label: "Incidents" },
      { to: "/staff/ops/checklists", label: "Checklists" },
    ],
  },
  {
    title: "Billing & Store",
    links: [
      { to: "/staff/invoices", label: "Invoices" },
      { to: "/staff/payments", label: "Payments" },
      { to: "/staff/store/packages", label: "Packages" },
      { to: "/staff/store/memberships", label: "Memberships" },
      { to: "/staff/store/gift-certificates", label: "Gift Certificates" },
      { to: "/staff/store/credits", label: "Store Credit" },
      { to: "/staff/store/coupons", label: "Coupons" },
      { to: "/staff/store/rewards", label: "Rewards" },
    ],
  },
  {
    title: "Comms & Reports",
    links: [
      { to: "/staff/comms/inbox", label: "Inbox" },
      { to: "/staff/comms/templates", label: "Templates" },
      { to: "/staff/comms/campaigns", label: "Campaigns" },
      { to: "/staff/reports", label: "Reports" },
    ],
  },
  {
    title: "Staff Tools",
    links: [
      { to: "/staff/timeclock", label: "Time Clock" },
      { to: "/staff/tips", label: "Tips" },
      { to: "/staff/commissions", label: "Commissions" },
      { to: "/staff/payroll", label: "Payroll" },
      { to: "/staff/staff/shifts", label: "Shifts" },
      { to: "/staff/staff/teams", label: "Teams" },
    ],
  },
  {
    title: "Admin",
    links: [
      { to: "/staff/admin/users", label: "Users" },
      { to: "/staff/admin/invitations", label: "Invitations" },
      { to: "/staff/admin/locations", label: "Locations" },
      { to: "/staff/admin/hours", label: "Hours" },
      { to: "/staff/admin/closures", label: "Closures" },
      { to: "/staff/admin/capacity", label: "Capacity" },
      { to: "/staff/admin/services", label: "Services" },
      { to: "/staff/admin/packages", label: "Packages" },
      { to: "/staff/admin/pricing", label: "Pricing Rules" },
      { to: "/staff/admin/tax", label: "Tax Rates" },
      { to: "/staff/admin/integrations", label: "Integrations" },
      { to: "/staff/admin/branding", label: "Branding" },
      { to: "/staff/admin/security", label: "Security" },
      { to: "/staff/admin/api-keys", label: "API Keys" },
      { to: "/staff/admin/account-codes", label: "Account Codes" },
      { to: "/staff/design/system", label: "Design System" },
    ],
  },
];

export default function StaffLayout() {
  const { user, logout } = useStaffAuth();
  const [quickSearchOpen, setQuickSearchOpen] = useState(false);

  useEffect(() => {
    Object.entries(PREFETCH_IMPORTERS).forEach(([path, importer]) => {
      attachPrefetch(`[data-prefetch-route="${path}"]`, importer);
    });
  }, []);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setQuickSearchOpen(true);
      }
      if (event.key === 'Escape') {
        setQuickSearchOpen(false);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  return (
    <div className="min-h-screen grid grid-cols-[260px_1fr] bg-slate-100">
      <SkipToContent />
      <aside
        className="bg-slate-900 text-slate-100 p-4 flex flex-col gap-3"
        role="navigation"
        aria-label="Staff sections"
      >
        <div className="text-lg font-semibold">EIPR Staff</div>
        {groups.map((g) => (
          <div key={g.title}>
            <div className="text-[11px] uppercase tracking-wide text-slate-400 mb-1">
              {g.title}
            </div>
            <nav className="flex flex-col gap-1">
              {g.links.map((l) => (
                <NavLink
                  key={l.to}
                  to={l.to}
                  end={l.end}
                  data-prefetch-route={PREFETCH_KEYS.has(l.to) ? l.to : undefined}
                  className={({ isActive }) =>
                    `px-3 py-2 rounded text-sm ${
                      isActive
                        ? "bg-orange-500 text-white"
                        : "text-slate-300 hover:text-white hover:bg-slate-800"
                    }`
                  }
                >
                  {l.label}
                </NavLink>
              ))}
            </nav>
          </div>
        ))}
        <div className="mt-auto text-xs text-slate-400 flex items-center justify-between gap-2">
          <span>{user?.email}</span>
          <button
            onClick={logout}
            className="inline-flex items-center gap-1 px-2 py-1 bg-slate-800 rounded"
            type="button"
          >
            <LogOut size={14} />
            Logout
          </button>
        </div>
      </aside>
      <main id="main" role="main" className="p-6" tabIndex={-1}>
        <div className="mb-4 flex items-center justify-end">
          <StaffSearchBar />
        </div>
        <Outlet />
      </main>
      <QuickSearch open={quickSearchOpen} onClose={() => setQuickSearchOpen(false)} />
    </div>
  );
}
