import { useMemo } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import PrintLayout from "../../../print/PrintLayout";
import { getInvoice } from "../../lib/billingFetchers";

type Params = {
  invoiceId?: string;
};

const formatMoney = (value: number | string) => `$${(Number(value) || 0).toFixed(2)}`;

export default function Receipt() {
  const { invoiceId = "" } = useParams<Params>();

  const { data } = useQuery({
    queryKey: ["invoice-print", invoiceId],
    queryFn: () => getInvoice(invoiceId),
    enabled: Boolean(invoiceId),
  });

  const invoice: any = data ?? {};
  const lines = useMemo(() => (Array.isArray(invoice.lines) ? invoice.lines : []), [invoice.lines]);

  const meta = useMemo(() => ([
    { label: "Invoice", value: invoiceId },
    { label: "Status", value: invoice?.status ?? "" },
    { label: "Created", value: invoice?.created_at ?? invoice?.issued_at ?? "" },
  ]), [invoiceId, invoice?.status, invoice?.created_at, invoice?.issued_at]);

  return (
    <PrintLayout title="Receipt" meta={meta}>
      <section className="print-block" aria-labelledby="receipt-party">
        <div className="print-section-title" id="receipt-party">Billing Details</div>
        <table className="print-table">
          <tbody>
            <tr>
              <th scope="row" style={{ width: "30%" }}>Owner</th>
              <td>{invoice.owner_name ?? invoice.owner_id ?? ""}</td>
            </tr>
            <tr>
              <th scope="row">Pet</th>
              <td>{invoice.pet_name ?? invoice.pet_id ?? ""}</td>
            </tr>
            <tr>
              <th scope="row">Payment Method</th>
              <td>{invoice.payment_method ?? invoice.payment_status ?? ""}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section className="print-block" aria-labelledby="receipt-lines">
        <div className="print-section-title" id="receipt-lines">Line Items</div>
        <table className="print-table">
          <thead>
            <tr>
              <th scope="col">Description</th>
              <th scope="col" style={{ textAlign: "right" }}>Qty</th>
              <th scope="col" style={{ textAlign: "right" }}>Unit</th>
              <th scope="col" style={{ textAlign: "right" }}>Amount</th>
            </tr>
          </thead>
          <tbody>
            {lines.map((line: any, index: number) => {
              const quantity = Number(line.qty ?? line.quantity ?? 1);
              const unit = Number(line.unit_price ?? line.price ?? 0);
              const amount = Number(line.total ?? quantity * unit);
              return (
                <tr key={line.id ?? index}>
                  <td>{line.description ?? line.name ?? ""}</td>
                  <td style={{ textAlign: "right" }}>{quantity}</td>
                  <td style={{ textAlign: "right" }}>{formatMoney(unit)}</td>
                  <td style={{ textAlign: "right" }}>{formatMoney(amount)}</td>
                </tr>
              );
            })}
            {lines.length === 0 && (
              <tr>
                <td colSpan={4} style={{ textAlign: "center", color: "var(--print-muted)" }}>
                  No line items.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      <section className="print-block" aria-labelledby="receipt-totals">
        <div className="print-section-title" id="receipt-totals">Totals</div>
        <table className="print-table" style={{ maxWidth: "320px", marginLeft: "auto" }}>
          <tbody>
            <tr>
              <th scope="row">Subtotal</th>
              <td style={{ textAlign: "right" }}>{formatMoney(invoice.subtotal ?? 0)}</td>
            </tr>
            <tr>
              <th scope="row">Discount</th>
              <td style={{ textAlign: "right" }}>{formatMoney(invoice.discount_total ?? 0)}</td>
            </tr>
            <tr>
              <th scope="row">Tax</th>
              <td style={{ textAlign: "right" }}>{formatMoney(invoice.tax_total ?? 0)}</td>
            </tr>
            <tr>
              <th scope="row">Payments</th>
              <td style={{ textAlign: "right" }}>{formatMoney(invoice.amount_paid ?? invoice.paid_total ?? 0)}</td>
            </tr>
            <tr>
              <th scope="row">Balance</th>
              <td style={{ textAlign: "right", fontWeight: 600 }}>{formatMoney(invoice.balance ?? invoice.total ?? 0)}</td>
            </tr>
          </tbody>
        </table>
      </section>

      {invoice.notes && (
        <section className="print-block" aria-labelledby="receipt-notes">
          <div className="print-section-title" id="receipt-notes">Notes</div>
          <div className="print-notes">{invoice.notes}</div>
        </section>
      )}
    </PrintLayout>
  );
}
