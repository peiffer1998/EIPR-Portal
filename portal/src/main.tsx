import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';

import App from './App';
import './index.css';
import ReportsAvailability from './staff/pages/Reports/Availability';
import ReservationDetail from './staff/pages/Reservations/Detail';
import { queryClient } from './lib/query';
import { AuthProvider } from './state/AuthContext';
import LoginRegister from './routes/LoginRegister';
import Dashboard from './routes/Dashboard';
import Pets from './routes/Pets';
import Reservations from './routes/Reservations';
import Invoices from './routes/Invoices';
import Uploads from './routes/Uploads';
import ReportCards from './routes/ReportCards';
import ReportCardDetail from './routes/ReportCardDetail';
import Store from './routes/Store';
import StorePackages from './routes/StorePackages';
import StoreGiftCerts from './routes/StoreGiftCerts';
import StoreBalances from './routes/StoreBalances';
import ProtectedRoute from './components/ProtectedRoute';

import { StaffAuthProvider } from './staff/state/StaffAuthContext';
import RequireStaff from './staff/components/RequireStaff';
import StaffLayout from './staff/components/StaffLayout';
import StaffLogin from './staff/pages/Login';
import StaffDashboard from './staff/pages/Dashboard';
import ReservationsList from './staff/pages/Reservations/List';
import NewReservation from './staff/pages/Reservations/NewReservation';
import NewGroom from './staff/pages/Grooming/NewAppointment';
import GroomingBoard from './staff/pages/Grooming/Board';
import CustomersList from './staff/pages/Customers';
import OwnerProfile from './staff/pages/Customers/OwnerProfile';
import PetsList from './staff/pages/Pets/List';
import PetProfile from './staff/pages/Pets/PetProfile';
import InvoicesList from './staff/pages/Invoices/List';
import InvoiceDetail from './staff/pages/Invoices/Detail';
import PaymentsList from './staff/pages/Payments/List';
import StaffStorePackages from './staff/pages/Store/Packages';
import StoreMemberships from './staff/pages/Store/Memberships';
import GiftCertificates from './staff/pages/Store/GiftCertificates';
import StoreCredits from './staff/pages/Store/Credits';
import StoreCoupons from './staff/pages/Store/Coupons';
import StoreRewards from './staff/pages/Store/Rewards';
import ReportsHub from './staff/pages/Reports';
import CommsInbox from './staff/pages/Comms/Inbox';
import CommsTemplates from './staff/pages/Comms/Templates';
import CommsCampaigns from './staff/pages/Comms/Campaigns';
import WaitlistPage from './staff/pages/Waitlist';
import PrecheckHome from './staff/pages/Precheck';
import TimeClock from './staff/pages/Staff/TimeClock';
import Tips from './staff/pages/Staff/Tips';
import Commissions from './staff/pages/Staff/Commissions';
import Payroll from './staff/pages/Staff/Payroll';
import BoardingCal from './staff/pages/Calendar/Boarding';
import DaycareCal from './staff/pages/Calendar/Daycare';
import GroomingCal from './staff/pages/Calendar/Grooming';
import CombinedCal from './staff/pages/Calendar/Combined';
import DaycareRoster from './staff/pages/Daycare/Roster';
import DaycareStanding from './staff/pages/Daycare/Standing';
import LodgingMap from './staff/pages/Boarding/LodgingMap';
import FeedingBoard from './staff/pages/Boarding/Feeding';
import MedsBoard from './staff/pages/Boarding/Meds';
import BelongingsBoard from './staff/pages/Boarding/Belongings';
import RunCards from './staff/pages/Boarding/RunCards';
import Incidents from './staff/pages/Ops/Incidents';
import Checklists from './staff/pages/Ops/Checklists';
import FilesPage from './staff/pages/Ops/Files';
import AdminUsers from './staff/pages/Admin/Users';
import AdminLocations from './staff/pages/Admin/Locations';
import AdminCapacity from './staff/pages/Admin/Capacity';
import AdminServices from './staff/pages/Admin/Services';
import AdminPackages from './staff/pages/Admin/Packages';
import AdminHours from './staff/pages/Admin/Hours';
import AdminClosures from './staff/pages/Admin/Closures';
import AdminPricing from './staff/pages/Admin/Pricing';
import AdminTax from './staff/pages/Admin/Tax';
import AdminIntegrations from './staff/pages/Admin/Integrations';
import AdminBranding from './staff/pages/Admin/Branding';
import AdminSecurity from './staff/pages/Admin/Security';
import AdminAPIKeys from './staff/pages/Admin/APIKeys';
import AdminAccountCodes from './staff/pages/Admin/AccountCodes';
import AdminInvitations from './staff/pages/Admin/Invitations';
import AcceptInvite from './public/pages/AcceptInvite';
import PrintRunCard from './staff/pages/Print/RunCard';
import PrintGroomTicket from './staff/pages/Print/GroomTicket';
import PrintFeeding from './staff/pages/Print/FeedingSheet';
import PrintMeds from './staff/pages/Print/MedsSheet';
import PrintReceipt from './staff/pages/Print/Receipt';

const root = document.getElementById('root');

if (!root) throw new Error('Root element not found');

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <StaffAuthProvider>
          <BrowserRouter>
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
                  <Route path="tax" element={<AdminTax />} />
                  <Route path="integrations" element={<AdminIntegrations />} />
                  <Route path="branding" element={<AdminBranding />} />
                  <Route path="security" element={<AdminSecurity />} />
                  <Route path="api-keys" element={<AdminAPIKeys />} />
                  <Route path="account-codes" element={<AdminAccountCodes />} />
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
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </StaffAuthProvider>
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
);
