import api from "../../lib/api";
import { getInvoice, capturePayment, refundPayment, emailReceipt as emailInvoiceReceipt } from "./billingFetchers";

const ok = <T>(promise: Promise<{ data: T }>): Promise<T> => promise.then((response) => response.data);

export async function findInvoiceForReservation(reservationId: string): Promise<any | null> {
  if (!reservationId) return null;
  try {
    const { data } = await api.get(`/reservations/${reservationId}/invoice`);
    if (data) return data;
  } catch (error) {
    // fall through to search endpoint
    console.warn("reservation invoice lookup failed", error);
  }

  try {
    const { data } = await api.get("/invoices", { params: { reservation_id: reservationId, limit: 1 } });
    if (Array.isArray((data as any)?.items)) {
      return (data as any).items[0] ?? null;
    }
    if (Array.isArray(data)) {
      return (data as any[])[0] ?? null;
    }
  } catch (error) {
    console.warn("invoice list lookup failed", error);
  }

  return null;
}

export async function refreshInvoice(invoiceId: string): Promise<any | null> {
  if (!invoiceId) return null;
  try {
    return await getInvoice(invoiceId);
  } catch (error) {
    console.warn("invoice refresh failed", error);
    return null;
  }
}

export async function captureInvoice(invoiceId: string) {
  if (!invoiceId) return null;
  return capturePayment(invoiceId);
}

export async function recordCashPayment(invoiceId: string, amount?: number) {
  if (!invoiceId) return null;
  const payload: Record<string, unknown> = { method: "cash" };
  if (typeof amount === "number" && Number.isFinite(amount) && amount > 0) {
    payload.amount = amount;
  }

  try {
    return await ok<any>(api.post(`/invoices/${invoiceId}/payments`, payload));
  } catch (error) {
    console.warn("record cash via payments endpoint failed", error);
  }

  try {
    return await ok<any>(api.post(`/payments`, { invoice_id: invoiceId, ...payload }));
  } catch (error) {
    console.warn("record cash via generic payments endpoint failed", error);
  }

  return null;
}

export async function refundInvoiceAmount(invoiceId: string, amount: number) {
  if (!invoiceId || !(amount > 0)) return null;
  return refundPayment(amount, invoiceId);
}

export async function emailReceipt(ownerId: string, invoiceId: string) {
  if (!invoiceId) return null;
  try {
    return await emailInvoiceReceipt(invoiceId);
  } catch (error) {
    console.warn("email receipt failed", error);
  }
  if (ownerId) {
    try {
      return await ok<any>(api.post("/comms/emails/send", { owner_id: ownerId, invoice_id: invoiceId }));
    } catch (error) {
      console.warn("fallback email receipt failed", error);
    }
  }
  return null;
}

export function receiptUrl(invoiceId: string): string {
  return `/staff/print/receipt/${invoiceId}`;
}
