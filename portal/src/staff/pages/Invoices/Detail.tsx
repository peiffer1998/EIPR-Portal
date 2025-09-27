import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import ConfirmDialog from "../../components/ConfirmDialog";
import LineItemEditor, { type Line as EditableLine } from "../../components/LineItemEditor";
import Money from "../../components/Money";
import {
  addLine,
  applyStoreCredit,
  capturePayment,
  computeTotals,
  emailReceipt,
  finalizeInvoice,
  getInvoice,
  refundPayment,
  removeLine,
  setDiscount,
  setTaxes,
  updateLine,
} from "../../lib/billingFetchers";

const DEFAULT_TAX_RATE = 0.07;

type Params = {
  invoiceId?: string;
};

type ConfirmState = {
  open: boolean;
  title?: string;
  message?: string;
  action?: () => Promise<void>;
};

export default function InvoiceDetail() {
  const { invoiceId = "" } = useParams<Params>();
  const queryClient = useQueryClient();

  const invoiceQuery = useQuery({
    queryKey: ["invoice", invoiceId],
    queryFn: () => getInvoice(invoiceId),
    enabled: Boolean(invoiceId),
  });

  const invoice: any = invoiceQuery.data ?? {
    id: invoiceId,
    lines: [],
    discount_total: 0,
    tax_total: 0,
    subtotal: 0,
    total: 0,
    status: "PENDING",
  };

  const [discountValue, setDiscountValue] = useState<number>(Number(invoice.discount_total || 0));
  const [taxRate, setTaxRate] = useState<number>(Number(invoice.tax_rate || DEFAULT_TAX_RATE));
  const [creditAmount, setCreditAmount] = useState<string>("");
  const [confirm, setConfirm] = useState<ConfirmState>({ open: false });

  useEffect(() => {
    setDiscountValue(Number(invoice.discount_total || 0));
    if (invoice.tax_rate != null) {
      setTaxRate(Number(invoice.tax_rate));
    }
  }, [invoice.discount_total, invoice.tax_rate]);

  const lines: EditableLine[] = useMemo(
    () =>
      (invoice.lines || []).map((line: any) => ({
        id: line.id,
        description: line.description,
        qty: Number(line.qty ?? line.quantity ?? 1),
        unit_price: Number(line.unit_price ?? line.price ?? 0),
        taxable: Boolean(line.taxable ?? true),
      })),
    [invoice.lines],
  );

  const totals = useMemo(() => computeTotals(lines, discountValue, taxRate), [lines, discountValue, taxRate]);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["invoice", invoiceId] });

  const addLineMutation = useMutation({
    mutationFn: (line: EditableLine) => addLine(invoiceId, line),
    onSuccess: invalidate,
  });

  const updateLineMutation = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: Partial<EditableLine> }) => updateLine(invoiceId, id, patch),
    onSuccess: invalidate,
  });

  const removeLineMutation = useMutation({
    mutationFn: (id: string) => removeLine(invoiceId, id),
    onSuccess: invalidate,
  });

  const discountMutation = useMutation({
    mutationFn: () => setDiscount(invoiceId, discountValue),
    onSuccess: invalidate,
  });

  const taxMutation = useMutation({
    mutationFn: () => setTaxes(invoiceId, totals.tax),
    onSuccess: invalidate,
  });

  const finalizeMutation = useMutation({
    mutationFn: () => finalizeInvoice(invoiceId),
    onSuccess: invalidate,
  });

  const emailMutation = useMutation({
    mutationFn: (address?: string) => emailReceipt(invoiceId, address),
  });

  const creditMutation = useMutation({
    mutationFn: (amount: number) => applyStoreCredit(invoiceId, amount),
    onSuccess: invalidate,
  });

  const captureMutation = useMutation({
    mutationFn: () => capturePayment(invoiceId, undefined),
    onSuccess: invalidate,
  });

  const refundMutation = useMutation({
    mutationFn: (amount: number) => refundPayment(amount, invoiceId, undefined),
    onSuccess: invalidate,
  });

  const openFinalizeConfirm = () =>
    setConfirm({
      open: true,
      title: "Finalize invoice",
      message: "Finalize this invoice and mark it as paid?",
      action: () => finalizeMutation.mutateAsync(),
    });

  const handleConfirmClose = () => setConfirm({ open: false });

  const payments: any[] = Array.isArray(invoice.payments) ? invoice.payments : [];

  const disabled = finalizeMutation.isPending || invoiceQuery.isLoading;

  return (
    <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
      <div className="grid gap-4">
        <div className="rounded-xl bg-white p-4 shadow">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold">Invoice {invoiceId}</h2>
              <p className="text-sm text-slate-600">Status: {invoice.status}</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                className="rounded border px-3 py-2"
                onClick={() => window.open(`/staff/print/receipt/${invoiceId}`, "_blank")}
              >
                Print receipt
              </button>
              <button
                type="button"
                className="rounded border px-3 py-2"
                onClick={() => emailMutation.mutate(undefined)}
                disabled={emailMutation.isPending}
              >
                {emailMutation.isPending ? "Sending…" : "Email receipt"}
              </button>
              <button
                type="button"
                className="rounded bg-slate-900 px-3 py-2 text-white"
                onClick={openFinalizeConfirm}
                disabled={invoice.status === "PAID" || disabled}
              >
                {finalizeMutation.isPending ? "Finalizing…" : "Finalize"}
              </button>
            </div>
          </div>
        </div>

        <LineItemEditor
          lines={lines}
          onAdd={(line) => addLineMutation.mutateAsync(line)}
          onUpdate={(id, patch) => updateLineMutation.mutateAsync({ id, patch })}
          onRemove={(id) => removeLineMutation.mutateAsync(id)}
        />

        <div className="grid gap-3 rounded-xl bg-white p-4 shadow md:grid-cols-3">
          <div>
            <label className="text-sm text-slate-600">Discount (absolute)</label>
            <input
              className="mt-1 w-full rounded border px-3 py-2"
              type="number"
              step="0.01"
              value={discountValue}
              onChange={(event) => setDiscountValue(Number(event.target.value) || 0)}
            />
            <button type="button" className="mt-2 rounded border px-3 py-2" onClick={() => discountMutation.mutate()}>
              Save discount
            </button>
          </div>
          <div>
            <label className="text-sm text-slate-600">Tax rate (preview)</label>
            <input
              className="mt-1 w-full rounded border px-3 py-2"
              type="number"
              step="0.001"
              value={taxRate}
              onChange={(event) => setTaxRate(Number(event.target.value) || 0)}
            />
            <button type="button" className="mt-2 rounded border px-3 py-2" onClick={() => taxMutation.mutate()}>
              Save tax
            </button>
          </div>
          <div>
            <label className="text-sm text-slate-600">Apply store credit</label>
            <div className="mt-1 flex gap-2">
              <input
                className="w-full rounded border px-3 py-2"
                type="number"
                step="0.01"
                value={creditAmount}
                onChange={(event) => setCreditAmount(event.target.value)}
              />
              <button
                type="button"
                className="rounded border px-3 py-2"
                onClick={() => {
                  const parsed = Number(creditAmount);
                  if (parsed > 0) {
                    creditMutation.mutate(parsed);
                    setCreditAmount("");
                  }
                }}
              >
                Apply
              </button>
            </div>
          </div>
        </div>

        <div className="rounded-xl bg-white p-4 shadow">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">Payments</h3>
            <div className="flex gap-2">
              <button
                type="button"
                className="rounded bg-slate-900 px-3 py-2 text-white"
                onClick={() => captureMutation.mutate()}
                disabled={invoice.status === "PAID" || captureMutation.isPending}
              >
                {captureMutation.isPending ? "Capturing…" : "Capture"}
              </button>
              <button
                type="button"
                className="rounded border px-3 py-2"
                onClick={() => {
                  const value = Number(window.prompt("Refund amount", "0") || 0);
                  if (value > 0) {
                    refundMutation.mutate(value);
                  }
                }}
                disabled={refundMutation.isPending}
              >
                {refundMutation.isPending ? "Refunding…" : "Refund"}
              </button>
            </div>
          </div>
          <div className="mt-3 grid gap-2 text-sm">
            {payments.length === 0 && <p className="text-slate-500">No payments recorded yet.</p>}
            {payments.map((payment) => (
              <div key={payment.id} className="rounded border border-slate-200 p-3">
                <div className="flex justify-between">
                  <span>{payment.id}</span>
                  <span>{payment.status}</span>
                </div>
                <div className="mt-1 flex justify-between text-slate-600">
                  <span>{payment.provider || ""}</span>
                  <Money value={payment.amount ?? 0} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="h-fit rounded-xl bg-white p-4 shadow">
        <h3 className="mb-3 font-semibold">Summary</h3>
        <div className="grid gap-2 text-sm">
          <div className="flex items-center justify-between">
            <span>Subtotal</span>
            <Money value={totals.subtotal} />
          </div>
          <div className="flex items-center justify-between">
            <span>Discount</span>
            <Money value={totals.discount} />
          </div>
          <div className="flex items-center justify-between">
            <span>Tax</span>
            <Money value={totals.tax} />
          </div>
          <div className="border-t pt-2 text-base font-semibold">
            <div className="flex items-center justify-between">
              <span>Total</span>
              <Money value={totals.total} />
            </div>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Preview totals are calculated client-side. Server totals remain the source of truth once saved.
          </p>
        </div>
      </div>

      <ConfirmDialog
        open={confirm.open}
        title={confirm.title}
        message={confirm.message}
        onCancel={handleConfirmClose}
        onConfirm={async () => {
          if (confirm.action) {
            await confirm.action();
          }
          handleConfirmClose();
        }}
      />
    </div>
  );
}
