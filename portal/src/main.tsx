import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';

import App from './App';
import './index.css';
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

const root = document.getElementById('root');

if (!root) throw new Error('Root element not found');

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
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
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
);
