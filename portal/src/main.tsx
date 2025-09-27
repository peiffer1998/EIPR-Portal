import { StrictMode, Suspense, lazy } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';

import App from './App';
import './index.css';
import './theme/theme.css';
import './a11y/focus.css';
import { startFlushLoop, startWebVitals } from './telemetry/rum';
import RouteMetrics from './telemetry/RouteMetrics';
import BoardingCheckIn from './kiosk/pages/BoardingCheckIn';
import BoardingCheckOut from './kiosk/pages/BoardingCheckOut';
import DaycareCheckIn from './kiosk/pages/DaycareCheckIn';
import DaycareCheckOut from './kiosk/pages/DaycareCheckOut';
import GroomingLane from './kiosk/pages/GroomingLane';
import KioskHome from './kiosk/pages/Home';
import KioskShell from './kiosk/pages/Shell';
import QuickPrint from './kiosk/pages/QuickPrint';
import ErrorBoundary from './ui/ErrorBoundary';
import ToastHost from './ui/Toast';
import DebugPanel from './telemetry/DebugPanel';
import Loading from './ui/Loading';
import { toggleDebugPanel } from './telemetry/telemetry';

import { queryClient } from './lib/query';
import { AuthProvider } from './state/AuthContext';

import ProtectedRoute from './components/ProtectedRoute';

import { StaffAuthProvider } from './staff/state/StaffAuthContext';
import RequireStaff from './staff/components/RequireStaff';
const ReportsAvailability = lazy(() => import('./staff/pages/Reports/Availability'));
const ReservationDetail = lazy(() => import('./staff/pages/Reservations/Detail'));
const LoginRegister = lazy(() => import('./routes/LoginRegister'));
const Dashboard = lazy(() => import('./routes/Dashboard'));
const Pets = lazy(() => import('./routes/Pets'));
const Reservations = lazy(() => import('./routes/Reservations'));
const Invoices = lazy(() => import('./routes/Invoices'));
const Uploads = lazy(() => import('./routes/Uploads'));
const ReportCards = lazy(() => import('./routes/ReportCards'));
const ReportCardDetail = lazy(() => import('./routes/ReportCardDetail'));
const Store = lazy(() => import('./routes/Store'));
const StorePackages = lazy(() => import('./routes/StorePackages'));
const StoreGiftCerts = lazy(() => import('./routes/StoreGiftCerts'));
const StoreBalances = lazy(() => import('./routes/StoreBalances'));
const StaffLayout = lazy(() => import('./staff/components/StaffLayout'));
const CheckoutPage = lazy(() => import('./staff/pages/Checkout'));
const StaffLogin = lazy(() => import('./staff/pages/Login'));
const StaffDashboard = lazy(() => import('./staff/pages/Dashboard'));
const ReservationsList = lazy(() => import('./staff/pages/Reservations/List'));
const NewReservation = lazy(() => import('./staff/pages/Reservations/NewReservation'));
const NewGroom = lazy(() => import('./staff/pages/Grooming/NewAppointment'));
const GroomingBoard = lazy(() => import('./staff/pages/Grooming/Board'));
const CustomersList = lazy(() => import('./staff/pages/Customers'));
const OwnerProfile = lazy(() => import('./staff/pages/Customers/OwnerProfile'));
const PetsList = lazy(() => import('./staff/pages/Pets/List'));
const PetProfile = lazy(() => import('./staff/pages/Pets/PetProfile'));
const InvoicesList = lazy(() => import('./staff/pages/Invoices/List'));
const InvoiceDetail = lazy(() => import('./staff/pages/Invoices/Detail'));
const PaymentsList = lazy(() => import('./staff/pages/Payments/List'));
const StaffStorePackages = lazy(() => import('./staff/pages/Store/Packages'));
const StoreMemberships = lazy(() => import('./staff/pages/Store/Memberships'));
const GiftCertificates = lazy(() => import('./staff/pages/Store/GiftCertificates'));
const StoreCredits = lazy(() => import('./staff/pages/Store/Credits'));
const StoreCoupons = lazy(() => import('./staff/pages/Store/Coupons'));
const StoreRewards = lazy(() => import('./staff/pages/Store/Rewards'));
const ReportsHub = lazy(() => import('./staff/pages/Reports'));
const CommsInbox = lazy(() => import('./staff/pages/Comms/Inbox'));
const CommsTemplates = lazy(() => import('./staff/pages/Comms/Templates'));
const CommsCampaigns = lazy(() => import('./staff/pages/Comms/Campaigns'));
const WaitlistPage = lazy(() => import('./staff/pages/Waitlist'));
const PrecheckHome = lazy(() => import('./staff/pages/Precheck'));
const TimeClock = lazy(() => import('./staff/pages/Staff/TimeClock'));
const PricingSandbox = lazy(() => import('./staff/pages/Tools/PricingSandbox'));
const Tips = lazy(() => import('./staff/pages/Staff/Tips'));
const Commissions = lazy(() => import('./staff/pages/Staff/Commissions'));
const Payroll = lazy(() => import('./staff/pages/Staff/Payroll'));
const BoardingCal = lazy(() => import('./staff/pages/Calendar/Boarding'));
const DaycareCal = lazy(() => import('./staff/pages/Calendar/Daycare'));
const GroomingCal = lazy(() => import('./staff/pages/Calendar/Grooming'));
const CombinedCal = lazy(() => import('./staff/pages/Calendar/Combined'));
const DaycareRoster = lazy(() => import('./staff/pages/Daycare/Roster'));
const DaycareStanding = lazy(() => import('./staff/pages/Daycare/Standing'));
const LodgingMap = lazy(() => import('./staff/pages/Boarding/LodgingMap'));
const FeedingBoard = lazy(() => import('./staff/pages/Boarding/Feeding'));
const MedsBoard = lazy(() => import('./staff/pages/Boarding/Meds'));
const BelongingsBoard = lazy(() => import('./staff/pages/Boarding/Belongings'));
const RunCards = lazy(() => import('./staff/pages/Boarding/RunCards'));
const Incidents = lazy(() => import('./staff/pages/Ops/Incidents'));
const Checklists = lazy(() => import('./staff/pages/Ops/Checklists'));
const FilesPage = lazy(() => import('./staff/pages/Ops/Files'));
const AdminUsers = lazy(() => import('./staff/pages/Admin/Users'));
const AdminLocations = lazy(() => import('./staff/pages/Admin/Locations'));
const AdminCapacity = lazy(() => import('./staff/pages/Admin/Capacity'));
const AdminServices = lazy(() => import('./staff/pages/Admin/Services'));
const AdminPackages = lazy(() => import('./staff/pages/Admin/Packages'));
const AdminHours = lazy(() => import('./staff/pages/Admin/Hours'));
const AdminClosures = lazy(() => import('./staff/pages/Admin/Closures'));
const AdminPricing = lazy(() => import('./staff/pages/Admin/Pricing'));
const AdminPerf = lazy(() => import('./staff/pages/Admin/Perf'));
const AdminTax = lazy(() => import('./staff/pages/Admin/Tax'));
const AdminIntegrations = lazy(() => import('./staff/pages/Admin/Integrations'));
const AdminBranding = lazy(() => import('./staff/pages/Admin/Branding'));
const AdminSecurity = lazy(() => import('./staff/pages/Admin/Security'));
const AdminAPIKeys = lazy(() => import('./staff/pages/Admin/APIKeys'));
const AdminAccountCodes = lazy(() => import('./staff/pages/Admin/AccountCodes'));
const AdminInvitations = lazy(() => import('./staff/pages/Admin/Invitations'));
const DesignSystem = lazy(() => import('./staff/pages/Design/System'));
const AcceptInvite = lazy(() => import('./public/pages/AcceptInvite'));
const NotFound = lazy(() => import('./public/pages/NotFound'));
const PrintRunCard = lazy(() => import('./staff/pages/Print/RunCard'));
const PrintGroomTicket = lazy(() => import('./staff/pages/Print/GroomTicket'));
const PrintFeeding = lazy(() => import('./staff/pages/Print/FeedingSheet'));
const PrintMeds = lazy(() => import('./staff/pages/Print/MedsSheet'));
const PrintReceipt = lazy(() => import('./staff/pages/Print/Receipt'));
const OwnerGuard = lazy(() => import('./owner/components/OwnerGuard'));
const OwnerShell = lazy(() => import('./owner/components/OwnerShell'));
const OwnerDashboard = lazy(() => import('./owner/pages/Dashboard'));
const OwnerPets = lazy(() => import('./owner/pages/Pets'));
const OwnerPetDetail = lazy(() => import('./owner/pages/Pets/Detail'));
const OwnerReservations = lazy(() => import('./owner/pages/Reservations'));
const OwnerReservationDetail = lazy(() => import('./owner/pages/Reservations/Detail'));
const OwnerGrooming = lazy(() => import('./owner/pages/Grooming'));
const OwnerPackages = lazy(() => import('./owner/pages/Packages'));
const OwnerCredits = lazy(() => import('./owner/pages/Credits'));
const OwnerInvoices = lazy(() => import('./owner/pages/Invoices'));
const OwnerReportCards = lazy(() => import('./owner/pages/ReportCards'));
const OwnerDocuments = lazy(() => import('./owner/pages/Documents'));
const OwnerPreferences = lazy(() => import('./owner/pages/Preferences'));

const root = document.getElementById('root');

if (!root) throw new Error('Root element not found');

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ErrorBoundary>
          <StaffAuthProvider>
            <BrowserRouter>
              <Suspense fallback={<Loading text="Loading view…" />}>
                <RouteMetrics />
                <Routes>
              <Route path="/login" element={<LoginRegister />} />
              <Route
                path="/"
                element={(
                  <ProtectedRoute>
                    <App />
                  </ProtectedRoute>
                )}
              >
                <Route index element={<Dashboard />} />
                <Route path="pets" element={<Pets />} />
                <Route path="reservations" element={<Reservations />} />
                <Route path="invoices" element={<Invoices />} />
                <Route path="report-cards" element={<ReportCards />} />
                <Route path="report-cards/:cardId" element={<ReportCardDetail />} />
                <Route path="store" element={<Store />}>
                  <Route index element={<StorePackages />} />
                  <Route path="packages" element={<StorePackages />} />
                  <Route path="gift-certificates" element={<StoreGiftCerts />} />
                  <Route path="balances" element={<StoreBalances />} />
                </Route>
                <Route path="uploads" element={<Uploads />} />
              </Route>

              <Route
                path="/owner"
                element={(
                  <ProtectedRoute>
                    <OwnerGuard>
                      <OwnerShell />
                    </OwnerGuard>
                  </ProtectedRoute>
                )}
              >
                <Route index element={<OwnerDashboard />} />
                <Route path="pets" element={<OwnerPets />} />
                <Route path="pets/:petId" element={<OwnerPetDetail />} />
                <Route path="reservations" element={<OwnerReservations />} />
                <Route
                  path="reservations/:reservationId"
                  element={<OwnerReservationDetail />}
                />
                <Route path="grooming" element={<OwnerGrooming />} />
                <Route path="packages" element={<OwnerPackages />} />
                <Route path="credits" element={<OwnerCredits />} />
                <Route path="invoices" element={<OwnerInvoices />} />
                <Route path="report-cards" element={<OwnerReportCards />} />
                <Route path="documents" element={<OwnerDocuments />} />
                <Route path="preferences" element={<OwnerPreferences />} />
              </Route>
              <Route path="/staff/login" element={<StaffLogin />} />
              <Route
                path="/staff"
                element={(
                  <RequireStaff>
                    <StaffLayout />
                  </RequireStaff>
                )}
              >
                <Route index element={<StaffDashboard />} />
                <Route path="checkout" element={<CheckoutPage />} />

                <Route path="calendar">
                  <Route path="boarding" element={<BoardingCal />} />
                  <Route path="daycare" element={<DaycareCal />} />
                  <Route path="grooming" element={<GroomingCal />} />
                  <Route path="combined" element={<CombinedCal />} />
                </Route>

                <Route path="reservations">
                  <Route index element={<ReservationsList />} />
                  <Route path=":id" element={<ReservationDetail />} />
                  <Route path="new" element={<NewReservation />} />
                </Route>

                <Route path="grooming">
                  <Route path="new" element={<NewGroom />} />
                  <Route path="board" element={<GroomingBoard />} />
                </Route>

                <Route path="customers">
                  <Route index element={<CustomersList />} />
                  <Route path=":ownerId" element={<OwnerProfile />} />
                </Route>

                <Route path="pets">
                  <Route path="list" element={<PetsList />} />
                  <Route path=":petId" element={<PetProfile />} />
                </Route>

                <Route path="boarding">
                  <Route path="lodging-map" element={<LodgingMap />} />
                  <Route path="feeding" element={<FeedingBoard />} />
                  <Route path="meds" element={<MedsBoard />} />
                  <Route path="belongings" element={<BelongingsBoard />} />
                  <Route path="run-cards" element={<RunCards />} />
                </Route>

                <Route path="daycare">
                  <Route path="roster" element={<DaycareRoster />} />
                  <Route path="standing" element={<DaycareStanding />} />
                </Route>

                <Route path="invoices">
                  <Route index element={<InvoicesList />} />
                  <Route path=":invoiceId" element={<InvoiceDetail />} />
                </Route>

                <Route path="payments" element={<PaymentsList />} />

                <Route path="store">
                  <Route path="packages" element={<StaffStorePackages />} />
                  <Route path="memberships" element={<StoreMemberships />} />
                  <Route path="gift-certificates" element={<GiftCertificates />} />
                  <Route path="credits" element={<StoreCredits />} />
                  <Route path="coupons" element={<StoreCoupons />} />
                  <Route path="rewards" element={<StoreRewards />} />
                </Route>

                <Route path="design/system" element={<DesignSystem />} />

                <Route path="tools">
                  <Route path="pricing" element={<PricingSandbox />} />
                </Route>

                <Route path="reports" element={<ReportsHub />} />
                <Route path="reports/availability" element={<ReportsAvailability />} />

                <Route path="comms">
                  <Route path="inbox" element={<CommsInbox />} />
                  <Route path="templates" element={<CommsTemplates />} />
                  <Route path="campaigns" element={<CommsCampaigns />} />
                </Route>

                <Route path="ops">
                  <Route path="incidents" element={<Incidents />} />
                  <Route path="checklists" element={<Checklists />} />
                  <Route path="files" element={<FilesPage />} />
                </Route>

                <Route path="waitlist" element={<WaitlistPage />} />
                <Route path="precheck" element={<PrecheckHome />} />
                <Route path="timeclock" element={<TimeClock />} />
                <Route path="tips" element={<Tips />} />
                <Route path="commissions" element={<Commissions />} />
                <Route path="payroll" element={<Payroll />} />
                <Route path="staff/shifts" element={<Checklists />} />
                <Route path="staff/teams" element={<Checklists />} />

                <Route path="admin">
                  <Route path="users" element={<AdminUsers />} />
                  <Route path="invitations" element={<AdminInvitations />} />
                  <Route path="locations" element={<AdminLocations />} />
                  <Route path="hours" element={<AdminHours />} />
                  <Route path="closures" element={<AdminClosures />} />
                  <Route path="capacity" element={<AdminCapacity />} />
                  <Route path="services" element={<AdminServices />} />
                  <Route path="packages" element={<AdminPackages />} />
                  <Route path="pricing" element={<AdminPricing />} />
                  <Route path="perf" element={<AdminPerf />} />
                  <Route path="tax" element={<AdminTax />} />
                  <Route path="integrations" element={<AdminIntegrations />} />
                  <Route path="branding" element={<AdminBranding />} />
                  <Route path="security" element={<AdminSecurity />} />
                  <Route path="api-keys" element={<AdminAPIKeys />} />
                  <Route path="account-codes" element={<AdminAccountCodes />} />
                </Route>

                <Route path="kiosk" element={<KioskShell />}>
                  <Route index element={<KioskHome />} />
                  <Route path="boarding/checkin" element={<BoardingCheckIn />} />
                  <Route path="boarding/checkout" element={<BoardingCheckOut />} />
                  <Route path="daycare/checkin" element={<DaycareCheckIn />} />
                  <Route path="daycare/checkout" element={<DaycareCheckOut />} />
                  <Route path="grooming" element={<GroomingLane />} />
                  <Route path="print" element={<QuickPrint />} />
                </Route>
                <Route path="print">
                  <Route path="run-card/:reservationId" element={<PrintRunCard />} />
                  <Route path="groom-ticket/:appointmentId" element={<PrintGroomTicket />} />
                  <Route path="feeding-sheet/:date" element={<PrintFeeding />} />
                  <Route path="meds-sheet/:date" element={<PrintMeds />} />
                  <Route path="receipt/:invoiceId" element={<PrintReceipt />} />
                </Route>
              </Route>

              <Route path="/invite/accept" element={<AcceptInvite />} />
              <Route path="/invite/accept/:token" element={<AcceptInvite />} />
              <Route path="*" element={<NotFound />} />
                </Routes>
              </Suspense>
            </BrowserRouter>
            <ToastHost />
            <DebugPanel />
          </StaffAuthProvider>
        </ErrorBoundary>
  </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
);

void startWebVitals();
startFlushLoop();

window.addEventListener('keydown', (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === '`') {
    event.preventDefault();
    toggleDebugPanel();
  }
});
