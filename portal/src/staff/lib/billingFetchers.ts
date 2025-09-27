import api from "../../lib/api";

const ok = <T>(promise: Promise<{ data: T }>): Promise<T> => promise.then((response) => response.data);

export type InvoiceLinePayload = {
  description: string;
  qty: number;
  unit_price: number;
  taxable: boolean;
};

export type InvoiceListResult = {
  items: any[];
  total: number;
  limit: number;
  offset: number;
};

export async function listInvoices(params: Record<string, unknown>): Promise<InvoiceListResult> {
  try {
    return await ok<InvoiceListResult>(api.get("/invoices", { params }));
  } catch {
    const rawLimit = Number((params as any)?.limit ?? 0);
    const rawOffset = Number((params as any)?.offset ?? 0);
    return { items: [], total: 0, limit: rawLimit || 0, offset: rawOffset || 0 };
  }
}

export async function getInvoice(id: string) {
  try {
    return await ok<any>(api.get(`/invoices/${id}`));
  } catch {
    return {
      id,
      status: "PENDING",
      lines: [],
      subtotal: 0,
      discount_total: 0,
      tax_total: 0,
      total: 0,
    } as any;
  }
}

export async function addLine(invoiceId: string, payload: InvoiceLinePayload) {
  try {
    return await ok<any>(api.post(`/invoices/${invoiceId}/lines`, payload));
  } catch {
    return await ok<any>(api.patch(`/invoices/${invoiceId}`, { add_line: payload }));
  }
}

export async function updateLine(invoiceId: string, lineId: string, patch: Partial<InvoiceLinePayload>) {
  try {
    return await ok<any>(api.patch(`/invoices/${invoiceId}/lines/${lineId}`, patch));
  } catch {
    return await ok<any>(api.patch(`/invoices/${invoiceId}`, { update_line: { id: lineId, ...patch } }));
  }
}

export async function removeLine(invoiceId: string, lineId: string) {
  try {
    return await ok<any>(api.delete(`/invoices/${invoiceId}/lines/${lineId}`));
  } catch {
    return await ok<any>(api.patch(`/invoices/${invoiceId}`, { remove_line: lineId }));
  }
}

export async function setDiscount(invoiceId: string, discount: number) {
  try {
    return await ok<any>(api.post(`/invoices/${invoiceId}/discount`, { amount: discount }));
  } catch {
    return await ok<any>(api.patch(`/invoices/${invoiceId}`, { discount_total: discount }));
  }
}

export async function setTaxes(invoiceId: string, tax: number) {
  try {
    return await ok<any>(api.post(`/invoices/${invoiceId}/tax`, { amount: tax }));
  } catch {
    return await ok<any>(api.patch(`/invoices/${invoiceId}`, { tax_total: tax }));
  }
}

export async function finalizeInvoice(invoiceId: string) {
  try {
    return await ok<any>(api.post(`/invoices/${invoiceId}/finalize`, {}));
  } catch {
    return await ok<any>(api.patch(`/invoices/${invoiceId}`, { status: "PAID" }));
  }
}

export async function emailReceipt(invoiceId: string, to?: string) {
  try {
    return await ok<any>(api.post(`/invoices/${invoiceId}/email`, { to }));
  } catch {
    try {
      return await ok<any>(api.post(`/comms/emails/send`, { invoice_id: invoiceId, to }));
    } catch {
      return { sent: false } as any;
    }
  }
}

export async function applyStoreCredit(invoiceId: string, amount: number) {
  try {
    return await ok<any>(api.post(`/invoices/${invoiceId}/apply-credit`, { amount }));
  } catch {
    return await ok<any>(api.patch(`/invoices/${invoiceId}`, { credit_applied: amount }));
  }
}

export async function listPayments(params: Record<string, unknown>) {
  try {
    return await ok<any[]>(api.get("/payments", { params }));
  } catch {
    return [] as any[];
  }
}

export async function capturePayment(invoiceId?: string, paymentId?: string) {
  try {
    if (paymentId) {
      return await ok<any>(api.post(`/payments/${paymentId}/capture`, {}));
    }
    return await ok<any>(api.post(`/invoices/${invoiceId}/capture`, {}));
  } catch {
    return { captured: false } as any;
  }
}

export async function refundPayment(amount: number, invoiceId?: string, paymentId?: string) {
  try {
    if (paymentId) {
      return await ok<any>(api.post(`/payments/${paymentId}/refund`, { amount }));
    }
    return await ok<any>(api.post(`/invoices/${invoiceId}/refund`, { amount }));
  } catch {
    return { refunded: false } as any;
  }
}

export type Line = {
  id?: string;
  description: string;
  qty: number;
  unit_price: number;
  taxable: boolean;
};

export type Totals = {
  subtotal: number;
  discount: number;
  tax: number;
  total: number;
};

export function computeTotals(lines: Line[], discount: number, taxRate: number): Totals {
  const subtotal = lines.reduce((sum, line) => {
    const qty = Number(line.qty) || 0;
    const unit = Number(line.unit_price) || 0;
    return sum + qty * unit;
  }, 0);

  const taxable = lines.reduce((sum, line) => {
    if (!line.taxable) return sum;
    const qty = Number(line.qty) || 0;
    const unit = Number(line.unit_price) || 0;
    return sum + qty * unit;
  }, 0);

  const discountAmount = Number(discount) || 0;
  const taxableBase = Math.max(0, taxable - discountAmount);
  const taxAmount = taxableBase * (Number(taxRate) || 0);
  const total = Math.max(0, subtotal - discountAmount + taxAmount);

  return {
    subtotal,
    discount: discountAmount,
    tax: taxAmount,
    total,
  };
}
