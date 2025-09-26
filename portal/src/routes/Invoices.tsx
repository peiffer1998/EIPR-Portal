import { useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { CardElement, Elements, useElements, useStripe } from '@stripe/react-stripe-js';
import { loadStripe } from '@stripe/stripe-js';

import { createPaymentIntent } from '../lib/portal';
import { usePortalMe } from '../lib/usePortalMe';
import { PORTAL_ME_QUERY_KEY } from '../lib/usePortalMe';

const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY ?? '');

const PaymentForm = ({
  invoiceId,
  onSuccess,
  amountDue,
}: {
  invoiceId: string;
  onSuccess: () => void;
  amountDue: string;
}) => {
  const stripe = useStripe();
  const elements = useElements();
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleSubmit = async () => {
    setIsProcessing(true);
    setError(null);
    try {
      const intent = await createPaymentIntent(invoiceId);
      const clientSecret = intent.client_secret;
      const isStub = clientSecret.endsWith('_secret_test');
      if (stripe && elements && !isStub) {
        const cardElement = elements.getElement(CardElement);
        if (!cardElement) {
          throw new Error('Card details are incomplete.');
        }
        const confirmation = await stripe.confirmCardPayment(clientSecret, {
          payment_method: {
            card: cardElement,
          },
        });
        if (confirmation.error) {
          throw new Error(confirmation.error.message ?? 'Payment failed');
        }
        if (confirmation.paymentIntent?.status !== 'succeeded') {
          throw new Error('Payment was not completed.');
        }
        cardElement.clear();
      }
      onSuccess();
    } catch (paymentError) {
      setError(paymentError instanceof Error ? paymentError.message : 'Payment failed');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4">
      <p className="text-sm text-slate-600">Amount due: ${Number(amountDue).toFixed(2)}</p>
      <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
        <CardElement options={{ hidePostalCode: true }} />
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
      <button
        type="button"
        onClick={handleSubmit}
        disabled={isProcessing}
        className="rounded-lg bg-orange-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-orange-600 disabled:cursor-not-allowed disabled:bg-orange-300"
      >
        {isProcessing ? 'Processing…' : 'Pay now'}
      </button>
    </div>
  );
};

const InvoicesInner = () => {
  const { data, isLoading } = usePortalMe();
  const queryClient = useQueryClient();
  const unpaid = data?.unpaid_invoices ?? [];
  const paid = data?.recent_paid_invoices ?? [];
  const [activeInvoice, setActiveInvoice] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const invalidate = useMutation({
    mutationFn: async () => queryClient.invalidateQueries({ queryKey: PORTAL_ME_QUERY_KEY }),
  });

  const handleSuccess = async () => {
    setMessage('Thank you! Your payment was recorded.');
    setActiveInvoice(null);
    await invalidate.mutateAsync();
  };

  const appearance = useMemo(() => ({ theme: 'stripe' as const }), []);

  if (isLoading) {
    return <p className="text-slate-500">Loading invoices…</p>;
  }

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">Outstanding invoices</h2>
        <p className="text-sm text-slate-500">Settle balances securely with your saved payment method or card.</p>
        {message && <p className="mt-3 rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700">{message}</p>}
        {unpaid.length === 0 ? (
          <p className="mt-4 text-sm text-slate-500">No open invoices. You’re all caught up!</p>
        ) : (
          <div className="mt-4 space-y-3">
            {unpaid.map((invoice) => (
              <div key={invoice.id} className="rounded-2xl bg-white p-4 shadow-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold text-slate-900">Invoice {invoice.id.slice(0, 8)}</p>
                    <p className="text-xs text-slate-400">Created {new Date(invoice.created_at).toLocaleString()}</p>
                  </div>
                  <span className="text-lg font-semibold text-slate-900">
                    ${Number(invoice.total).toFixed(2)}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveInvoice((prev) => (prev === invoice.id ? null : invoice.id))}
                  className="mt-3 text-sm font-medium text-orange-600 hover:underline"
                >
                  {activeInvoice === invoice.id ? 'Hide payment form' : 'Pay this invoice'}
                </button>
                {activeInvoice === invoice.id && (
                  <div className="mt-4">
                    <Elements stripe={stripePromise} options={{ appearance }}>
                      <PaymentForm invoiceId={invoice.id} onSuccess={handleSuccess} amountDue={invoice.total} />
                    </Elements>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <h3 className="text-lg font-semibold text-slate-900">Recent payments</h3>
        {paid.length === 0 ? (
          <p className="text-sm text-slate-500">No payments recorded yet.</p>
        ) : (
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            {paid.map((invoice) => (
              <div key={invoice.id} className="rounded-2xl bg-white p-4 shadow-sm">
                <p className="text-sm font-semibold text-slate-900">Invoice {invoice.id.slice(0, 8)}</p>
                <p className="text-xs text-slate-400">Paid {invoice.paid_at ? new Date(invoice.paid_at).toLocaleString() : 'Just now'}</p>
                <p className="mt-2 text-sm text-slate-600">Total: ${Number(invoice.total).toFixed(2)}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
};

const Invoices = () => (
  <InvoicesInner />
);

export default Invoices;
