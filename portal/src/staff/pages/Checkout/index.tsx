import React from "react";

import { useCheckoutCart } from "../../state/CheckoutCart";
import {
  findInvoiceForReservation,
  refreshInvoice,
  captureInvoice,
  recordCashPayment,
  refundInvoiceAmount,
  emailReceipt,
  receiptUrl,
} from "../../lib/tenderFetchers";
import { checkOut } from "../../lib/reservationOps";
import { toast } from "../../../ui/Toast";

const currency = (value: unknown) => {
  const amount = Number(value) || 0;
  return `$${amount.toFixed(2)}`;
};

type Row = {
  reservationId: string;
  ownerId: string;
  petName?: string;
  petId?: string;
  service?: string;
  invoice?: any | null;
  loading?: boolean;
  selected: boolean;
};

export default function CheckoutPage(): JSX.Element {
  const { cart, remove, clear } = useCheckoutCart();
  const [rows, setRows] = React.useState<Row[]>([]);
  const [busy, setBusy] = React.useState(false);
  const rowsRef = React.useRef<Row[]>([]);

  React.useEffect(() => {
    rowsRef.current = rows;
  }, [rows]);

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      const next: Row[] = [];
      for (const item of cart.items) {
        const reservationId = item.reservationId;
        let invoice: any | null = null;
        try {
          invoice = await findInvoiceForReservation(reservationId);
        } catch (error) {
          console.warn("invoice lookup failed", error);
        }
        if (cancelled) return;
        next.push({
          reservationId,
          ownerId: item.ownerId,
          petName: item.petName,
          petId: item.petId,
          service: item.service,
          invoice,
          selected: true,
        });
      }
      if (!cancelled) {
        setRows(next);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [cart.items]);

  const selectedRows = React.useMemo(() => rows.filter((row) => row.selected), [rows]);

  const refreshRow = React.useCallback(async (reservationId: string) => {
    setRows((prev) => prev.map((row) => (row.reservationId === reservationId ? { ...row, loading: true } : row)));
    const currentRow = rowsRef.current.find((row) => row.reservationId === reservationId);
    const invoiceId = currentRow?.invoice?.id;
    if (!invoiceId) {
      setRows((prev) => prev.map((row) => (row.reservationId === reservationId ? { ...row, loading: false } : row)));
      return;
    }
    const updatedInvoice = await refreshInvoice(invoiceId);
    setRows((prev) =>
      prev.map((row) =>
        row.reservationId === reservationId
          ? { ...row, invoice: updatedInvoice ?? row.invoice, loading: false }
          : row,
      ),
    );
  }, []);

  const handleRemove = React.useCallback(
    (reservationId: string) => {
      remove(reservationId);
      setRows((prev) => prev.filter((row) => row.reservationId !== reservationId));
    },
    [remove],
  );

  const toggleRow = React.useCallback((reservationId: string) => {
    setRows((prev) =>
      prev.map((row) =>
        row.reservationId === reservationId ? { ...row, selected: !row.selected } : row,
      ),
    );
  }, []);

  const allSelected = rows.length > 0 && rows.every((row) => row.selected);
  const toggleAll = React.useCallback(() => {
    setRows((prev) => prev.map((row) => ({ ...row, selected: !allSelected })));
  }, [allSelected]);

  const handleCheckOutSelected = React.useCallback(async () => {
    const toProcess = rowsRef.current.filter((row) => row.selected);
    if (!toProcess.length) {
      toast("Select at least one reservation to check out.", "info");
      return;
    }

    setBusy(true);
    const completed: string[] = [];
    for (const row of toProcess) {
      try {
        await checkOut(row.reservationId);
        completed.push(row.reservationId);
      } catch (error) {
        console.warn("check-out failed", error);
        toast(`Unable to check out ${row.petName ?? "reservation"}.`, "error");
      }
    }
    if (completed.length) {
      completed.forEach((reservationId) => remove(reservationId));
      setRows((prev) => prev.filter((row) => !completed.includes(row.reservationId)));
      toast(`Checked out ${completed.length} reservation${completed.length === 1 ? "" : "s"}.`, "success");
    }
    setBusy(false);
  }, [remove]);

  const handleCaptureSelected = React.useCallback(async () => {
    const toProcess = rowsRef.current.filter((row) => row.selected && row.invoice?.id);
    if (!toProcess.length) {
      toast("Select at least one invoice to capture.", "info");
      return;
    }
    setBusy(true);
    for (const row of toProcess) {
      try {
        await captureInvoice(row.invoice.id);
        await refreshRow(row.reservationId);
      } catch (error) {
        console.warn("capture failed", error);
        toast(`Unable to capture payment for ${row.petName ?? "reservation"}.`, "error");
      }
    }
    setBusy(false);
  }, [refreshRow]);

  const handleCashSelected = React.useCallback(async () => {
    const toProcess = rowsRef.current.filter((row) => row.selected && row.invoice?.id);
    if (!toProcess.length) {
      toast("Select at least one invoice to record cash payment.", "info");
      return;
    }
    const amountInput = window.prompt("Cash amount (leave blank for invoice totals)", "");
    const amount = amountInput ? Number(amountInput) : undefined;
    if (amountInput && !(amount > 0)) {
      toast("Enter a valid positive amount.", "error");
      return;
    }
    setBusy(true);
    for (const row of toProcess) {
      try {
        await recordCashPayment(row.invoice.id, amount);
        await refreshRow(row.reservationId);
      } catch (error) {
        console.warn("cash record failed", error);
        toast(`Unable to record cash for ${row.petName ?? "reservation"}.`, "error");
      }
    }
    setBusy(false);
  }, [refreshRow]);

  const handleRefundSelected = React.useCallback(async () => {
    const toProcess = rowsRef.current.filter((row) => row.selected && row.invoice?.id);
    if (!toProcess.length) {
      toast("Select at least one invoice to refund.", "info");
      return;
    }
    const amount = Number(window.prompt("Refund amount (applied to each selected invoice)", "0") ?? 0);
    if (!(amount > 0)) {
      toast("Enter a valid positive refund amount.", "error");
      return;
    }
    setBusy(true);
    for (const row of toProcess) {
      try {
        await refundInvoiceAmount(row.invoice.id, amount);
        await refreshRow(row.reservationId);
      } catch (error) {
        console.warn("refund failed", error);
        toast(`Unable to refund ${row.petName ?? "reservation"}.`, "error");
      }
    }
    setBusy(false);
  }, [refreshRow]);

  const handleEmailSelected = React.useCallback(async () => {
    const toProcess = rowsRef.current.filter((row) => row.selected && row.invoice?.id);
    if (!toProcess.length) {
      toast("Select at least one invoice to email.", "info");
      return;
    }
    setBusy(true);
    for (const row of toProcess) {
      try {
        await emailReceipt(row.ownerId, row.invoice.id);
      } catch (error) {
        console.warn("email receipt failed", error);
        toast(`Unable to email receipt for ${row.petName ?? "reservation"}.`, "error");
      }
    }
    setBusy(false);
    toast("Receipt emails queued.", "success");
  }, []);

  const handlePrintSelected = React.useCallback(() => {
    const toProcess = rowsRef.current.filter((row) => row.selected && row.invoice?.id);
    if (!toProcess.length) {
      toast("Select at least one invoice to print.", "info");
      return;
    }
    toProcess.forEach((row) => {
      window.open(receiptUrl(row.invoice.id), "_blank", "noopener");
    });
  }, []);

  return (
    <div className="grid gap-4">
      <div className="rounded-xl bg-white p-4 shadow">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-lg font-semibold text-slate-900">Checkout</div>
            <div className="text-sm text-slate-600">
              {rows.length} reservation{rows.length === 1 ? "" : "s"}
              {cart.ownerId ? ` • owner ${cart.ownerId}` : ""}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              className="rounded border border-slate-200 px-3 py-1 text-sm"
              onClick={() => {
                clear();
                setRows([]);
              }}
              disabled={!rows.length}
            >
              Clear Cart
            </button>
            <button
              className="rounded bg-slate-900 px-3 py-1 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
              onClick={handleCheckOutSelected}
              disabled={busy || !selectedRows.length}
            >
              Check-Out Selected
            </button>
            <button
              className="rounded bg-emerald-600 px-3 py-1 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
              onClick={handleCaptureSelected}
              disabled={busy || !selectedRows.length}
            >
              Capture Card
            </button>
            <button
              className="rounded bg-slate-800 px-3 py-1 text-sm font-semibold text-white hover:bg-slate-700 disabled:opacity-50"
              onClick={handleCashSelected}
              disabled={busy || !selectedRows.length}
            >
              Record Cash
            </button>
            <button
              className="rounded border border-slate-200 px-3 py-1 text-sm hover:bg-slate-100 disabled:opacity-50"
              onClick={handleRefundSelected}
              disabled={busy || !selectedRows.length}
            >
              Partial Refund
            </button>
            <button
              className="rounded border border-slate-200 px-3 py-1 text-sm hover:bg-slate-100 disabled:opacity-50"
              onClick={handleEmailSelected}
              disabled={busy || !selectedRows.length}
            >
              Email Receipts
            </button>
            <button
              className="rounded border border-slate-200 px-3 py-1 text-sm hover:bg-slate-100 disabled:opacity-50"
              onClick={handlePrintSelected}
              disabled={!selectedRows.length}
            >
              Print Receipts
            </button>
          </div>
        </div>
      </div>

      <div className="rounded-xl bg-white p-4 shadow">
        <div className="mb-3 flex items-center justify-between">
          <div className="font-semibold text-slate-900">Reservations</div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={allSelected} onChange={toggleAll} />
            <span>Select all</span>
          </label>
        </div>

        <div className="overflow-auto">
          <table className="min-w-full text-sm">
            <thead className="text-left text-slate-500">
              <tr>
                <th className="px-3 py-2">Select</th>
                <th className="px-3 py-2">Pet</th>
                <th className="px-3 py-2">Service</th>
                <th className="px-3 py-2">Invoice</th>
                <th className="px-3 py-2">Balance</th>
                <th className="px-3 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.reservationId} className="border-t">
                  <td className="px-3 py-2 align-middle">
                    <input
                      type="checkbox"
                      checked={row.selected}
                      onChange={() => toggleRow(row.reservationId)}
                    />
                  </td>
                  <td className="px-3 py-2 align-middle">
                    <div className="font-medium text-slate-900">{row.petName ?? row.petId ?? "Pet"}</div>
                    <div className="text-xs text-slate-500">Reservation {row.reservationId}</div>
                  </td>
                  <td className="px-3 py-2 align-middle text-slate-600">{row.service ?? "—"}</td>
                  <td className="px-3 py-2 align-middle">
                    {row.invoice ? (
                      <div className="flex flex-col">
                        <span className="font-mono text-xs">{row.invoice.id}</span>
                        <span className="text-xs text-slate-500">{row.invoice.status}</span>
                      </div>
                    ) : (
                      <span className="text-slate-400">No invoice</span>
                    )}
                  </td>
                  <td className="px-3 py-2 align-middle text-right">
                    {row.invoice ? currency(row.invoice.balance ?? row.invoice.total ?? 0) : "—"}
                  </td>
                  <td className="px-3 py-2 align-middle text-right">
                    {row.invoice?.id && (
                      <a className="mr-3 text-blue-700" href={receiptUrl(row.invoice.id)} target="_blank" rel="noreferrer">
                        Print
                      </a>
                    )}
                    <button
                      type="button"
                      className="text-red-600"
                      onClick={() => handleRemove(row.reservationId)}
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
              {!rows.length && (
                <tr>
                  <td colSpan={6} className="px-3 py-6 text-center text-slate-500">
                    Cart is empty.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
