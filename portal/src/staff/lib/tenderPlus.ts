import api from "../../lib/api";
import type { DashboardReservation } from "./dashboardFetchers";
import {
  findInvoiceForReservation,
  refreshInvoice,
  captureInvoice,
  recordCashPayment,
  refundInvoiceAmount,
  emailReceipt,
  receiptUrl,
} from "./tenderFetchers";

export async function ensureInvoiceForReservation(reservationId: string): Promise<any | null> {
  if (!reservationId) return null;
  const existing = await findInvoiceForReservation(reservationId);
  if (existing) return existing;

  // Preferred endpoint: POST /invoices { reservation_id }
  try {
    const { data } = await api.post("/invoices", { reservation_id: reservationId });
    return data ?? null;
  } catch (primaryError) {
    console.warn("create invoice via /invoices failed", primaryError);
  }

  // Fallback: POST /reservations/:id/invoice
  try {
    const { data } = await api.post(`/reservations/${reservationId}/invoice`, {});
    return data ?? null;
  } catch (fallbackError) {
    console.warn("create invoice via reservation endpoint failed", fallbackError);
  }

  return null;
}

export async function addInvoiceLine(
  invoiceId: string,
  line: { description: string; qty: number; unit_price: number; taxable?: boolean },
): Promise<any | null> {
  if (!invoiceId) return null;
  try {
    const { data } = await api.post(`/invoices/${invoiceId}/lines`, line);
    return data ?? null;
  } catch (primaryError) {
    console.warn("add invoice line via POST failed", primaryError);
  }

  try {
    const { data } = await api.patch(`/invoices/${invoiceId}`, { add_line: line });
    return data ?? null;
  } catch (fallbackError) {
    console.warn("add invoice line via PATCH failed", fallbackError);
  }

  return null;
}

export async function getReservation(reservationId: string): Promise<DashboardReservation | null> {
  if (!reservationId) return null;
  try {
    const { data } = await api.get(`/reservations/${reservationId}`);
    return data ?? null;
  } catch (error) {
    console.warn("reservation fetch failed", error);
    return null;
  }
}

export function isLateReservation(reservation: Pick<DashboardReservation, "end_at" | "status"> | null | undefined): boolean {
  if (!reservation?.end_at) return false;
  try {
    const end = new Date(reservation.end_at);
    const now = new Date();
    if (Number.isNaN(end.getTime())) return false;
    const status = (reservation.status ?? "").toUpperCase();
    return status === "CHECKED_IN" && end < now;
  } catch (error) {
    console.warn("late reservation check failed", error);
    return false;
  }
}

export {
  findInvoiceForReservation,
  refreshInvoice,
  captureInvoice,
  recordCashPayment,
  refundInvoiceAmount,
  emailReceipt,
  receiptUrl,
};
