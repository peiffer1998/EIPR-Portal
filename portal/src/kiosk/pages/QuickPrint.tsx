import { useState } from 'react';

export default function QuickPrint() {
  const [reservationId, setReservationId] = useState('');
  const [appointmentId, setAppointmentId] = useState('');
  const [invoiceId, setInvoiceId] = useState('');

  const linkOrDisabled = (href: string | null) => (href ? href : '#');

  return (
    <div className="grid gap-4">
      <div className="grid md:grid-cols-[1fr_auto] gap-2 items-end">
        <label className="text-lg grid">
          <span className="text-sm text-slate-600">Reservation ID</span>
          <input
            className="text-xl border rounded px-3 py-2"
            value={reservationId}
            onChange={(event) => setReservationId(event.target.value)}
            placeholder="Reservation ID"
          />
        </label>
        <a
          className="px-4 py-3 rounded border text-lg"
          href={linkOrDisabled(reservationId ? `/staff/print/run-card/${reservationId}` : null)}
          target="_blank"
          rel="noreferrer"
        >
          Run Card
        </a>
      </div>
      <div className="grid md:grid-cols-[1fr_auto] gap-2 items-end">
        <label className="text-lg grid">
          <span className="text-sm text-slate-600">Appointment ID</span>
          <input
            className="text-xl border rounded px-3 py-2"
            value={appointmentId}
            onChange={(event) => setAppointmentId(event.target.value)}
            placeholder="Appointment ID"
          />
        </label>
        <a
          className="px-4 py-3 rounded border text-lg"
          href={linkOrDisabled(appointmentId ? `/staff/print/groom-ticket/${appointmentId}` : null)}
          target="_blank"
          rel="noreferrer"
        >
          Groom Ticket
        </a>
      </div>
      <div className="grid md:grid-cols-[1fr_auto] gap-2 items-end">
        <label className="text-lg grid">
          <span className="text-sm text-slate-600">Invoice ID</span>
          <input
            className="text-xl border rounded px-3 py-2"
            value={invoiceId}
            onChange={(event) => setInvoiceId(event.target.value)}
            placeholder="Invoice ID"
          />
        </label>
        <a
          className="px-4 py-3 rounded border text-lg"
          href={linkOrDisabled(invoiceId ? `/staff/print/receipt/${invoiceId}` : null)}
          target="_blank"
          rel="noreferrer"
        >
          Receipt
        </a>
      </div>
    </div>
  );
}
