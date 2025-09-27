import { useEffect } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { getInvoice } from "../../lib/billingFetchers";

type Params = {
  invoiceId?: string;
};

const formatMoney = (value: number | string) => `$${(Number(value) || 0).toFixed(2)}`;

export default function Receipt() {
  const { invoiceId = "" } = useParams<Params>();

  const invoiceQuery = useQuery({
    queryKey: ["invoice", invoiceId, "print"],
    queryFn: () => getInvoice(invoiceId),
    enabled: Boolean(invoiceId),
  });

  useEffect(() => {
    if (!invoiceQuery.isLoading) {
      const handle = setTimeout(() => window.print(), 100);
      return () => clearTimeout(handle);
    }
    return undefined;
  }, [invoiceQuery.isLoading]);

  const invoice: any = invoiceQuery.data ?? {};
  const lines = Array.isArray(invoice.lines) ? invoice.lines : [];

  return (
    <div style={{ fontFamily: "ui-sans-serif", padding: "24px", lineHeight: 1.45 }}>
      <header style={{ marginBottom: "16px" }}>
        <h1 style={{ margin: 0, fontSize: "26px" }}>Receipt</h1>
        <div style={{ color: "#475569", marginTop: "4px" }}>Invoice #{invoiceId}</div>
      </header>

      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px" }}>
        <div>
          <div style={{ fontSize: "12px", fontWeight: 600, textTransform: "uppercase", color: "#64748b" }}>Owner</div>
          <div>{invoice.owner_name || invoice.owner_id || ""}</div>
        </div>
        <div>
          <div style={{ fontSize: "12px", fontWeight: 600, textTransform: "uppercase", color: "#64748b" }}>Pet</div>
          <div>{invoice.pet_name || invoice.pet_id || ""}</div>
        </div>
        <div>
          <div style={{ fontSize: "12px", fontWeight: 600, textTransform: "uppercase", color: "#64748b" }}>Status</div>
          <div>{invoice.status || ""}</div>
        </div>
      </section>

      <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "18px", fontSize: "12px" }}>
        <thead>
          <tr>
            <th align="left" style={{ borderBottom: "1px solid #e2e8f0", padding: "6px" }}>Description</th>
            <th align="right" style={{ borderBottom: "1px solid #e2e8f0", padding: "6px" }}>Qty</th>
            <th align="right" style={{ borderBottom: "1px solid #e2e8f0", padding: "6px" }}>Unit</th>
            <th align="right" style={{ borderBottom: "1px solid #e2e8f0", padding: "6px" }}>Amount</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line: any, index: number) => {
            const qty = Number(line.qty ?? line.quantity ?? 1);
            const unit = Number(line.unit_price ?? line.price ?? 0);
            const amount = qty * unit;
            return (
              <tr key={line.id ?? index}>
                <td style={{ borderBottom: "1px solid #f1f5f9", padding: "6px" }}>{line.description}</td>
                <td align="right" style={{ borderBottom: "1px solid #f1f5f9", padding: "6px" }}>{qty}</td>
                <td align="right" style={{ borderBottom: "1px solid #f1f5f9", padding: "6px" }}>{formatMoney(unit)}</td>
                <td align="right" style={{ borderBottom: "1px solid #f1f5f9", padding: "6px" }}>{formatMoney(amount)}</td>
              </tr>
            );
          })}
          {lines.length === 0 && (
            <tr>
              <td colSpan={4} style={{ padding: "8px", color: "#64748b", textAlign: "center" }}>No line items.</td>
            </tr>
          )}
        </tbody>
      </table>

      <div style={{ marginTop: "18px", marginLeft: "auto", maxWidth: "280px" }}>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span>Subtotal</span>
          <span>{formatMoney(invoice.subtotal ?? 0)}</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span>Discount</span>
          <span>{formatMoney(invoice.discount_total ?? 0)}</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span>Tax</span>
          <span>{formatMoney(invoice.tax_total ?? 0)}</span>
        </div>
        <div style={{ borderTop: "1px solid #cbd5f5", marginTop: "6px", paddingTop: "6px", display: "flex", justifyContent: "space-between", fontWeight: 600 }}>
          <span>Total</span>
          <span>{formatMoney(invoice.total ?? 0)}</span>
        </div>
      </div>
    </div>
  );
}
