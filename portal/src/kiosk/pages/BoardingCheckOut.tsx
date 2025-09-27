import { useState } from 'react';

import ScanBox from '../components/ScanBox';
import TenderBar from '../components/TenderBar';
import {
  captureInvoice,
  checkOutReservation,
  getInvoiceForReservation,
  getReservation,
  markCashPaid,
} from '../lib/fetchers';

type Reservation = Record<string, any> & {
  id: string;
  pet?: { name?: string } | null;
  pet_id?: string;
  reservation_type?: string;
};

type Invoice = {
  id: string;
  total?: number | string;
};

export default function BoardingCheckOut() {
  const [reservation, setReservation] = useState<Reservation | null>(null);
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [loading, setLoading] = useState(false);

  const loadReservation = async (id: string) => {
    setLoading(true);
    try {
      const [resv, inv] = await Promise.all([
        getReservation(id) as Promise<Reservation>,
        getInvoiceForReservation(id),
      ]);
      setReservation(resv);
      setInvoice(inv as Invoice | null);
    } catch {
      window.alert('Unable to load reservation');
      setReservation(null);
      setInvoice(null);
    } finally {
      setLoading(false);
    }
  };

  const performCheckout = async () => {
    if (!reservation) return;
    setLoading(true);
    try {
      await checkOutReservation(reservation.id);
      window.alert('Reservation checked out');
      setReservation(null);
      setInvoice(null);
    } catch {
      window.alert('Check-out failed');
    } finally {
      setLoading(false);
    }
  };

  const handleCapture = async () => {
    if (!invoice) {
      window.alert('No invoice available');
      return;
    }

    try {
      await captureInvoice(invoice.id);
      window.alert('Invoice captured');
    } catch {
      window.alert('Capture failed');
    }
  };

  const handleCash = async () => {
    if (!invoice) {
      window.alert('No invoice available');
      return;
    }

    try {
      await markCashPaid(invoice.id);
      window.alert('Cash payment recorded');
    } catch {
      window.alert('Failed to record cash payment');
    }
  };

  return (
    <div className="grid gap-4">
      <ScanBox label="Scan or type reservation ID" onSubmit={loadReservation} />
      {loading ? <div className="text-slate-600">Working…</div> : null}
      {reservation ? (
        <div className="grid gap-3">
          <div className="text-2xl font-semibold">
            {reservation.pet?.name ?? reservation.pet_id} • {reservation.reservation_type ?? 'Boarding'}
          </div>
          <div className="flex gap-2 flex-wrap">
            <a
              className="px-4 py-3 rounded border text-xl"
              href={`/staff/print/run-card/${reservation.id}`}
              target="_blank"
              rel="noreferrer"
            >
              Run Card
            </a>
            {invoice ? (
              <a
                className="px-4 py-3 rounded border text-xl"
                href={`/staff/print/receipt/${invoice.id}`}
                target="_blank"
                rel="noreferrer"
              >
                Receipt
              </a>
            ) : null}
          </div>
          {invoice ? <TenderBar total={invoice.total ?? 0} onCard={handleCapture} onCash={handleCash} /> : null}
          <div>
            <button
              type="button"
              className="px-5 py-4 rounded bg-orange-500 text-white text-xl mt-2"
              onClick={performCheckout}
              disabled={loading}
            >
              Complete Check-Out
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
