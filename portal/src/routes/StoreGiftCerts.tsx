import type { FormEvent } from 'react';
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import {
  buyPortalGiftCertificate,
  redeemPortalGiftCertificate,
  type PortalPurchaseResponse,
} from '../lib/portal';
import { STORE_BALANCES_QUERY_KEY } from '../lib/storeQueries';

const StoreGiftCerts = () => {
  const queryClient = useQueryClient();
  const [purchaseAmount, setPurchaseAmount] = useState('50.00');
  const [recipientEmail, setRecipientEmail] = useState('');
  const [redeemCode, setRedeemCode] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [redeemMessage, setRedeemMessage] = useState<string | null>(null);
  const [redeemError, setRedeemError] = useState<string | null>(null);

  const purchaseMutation = useMutation({
    mutationFn: () =>
      buyPortalGiftCertificate({
        amount: purchaseAmount,
        recipientEmail: recipientEmail || undefined,
      }),
    onSuccess: (response: PortalPurchaseResponse) => {
      setMessage(
        `Gift certificate created. Invoice ${response.invoice_id.slice(0, 8)} is ready to pay. ` +
          (response.gift_certificate_code ? `Code: ${response.gift_certificate_code}` : ''),
      );
      setError(null);
      queryClient.invalidateQueries({ queryKey: STORE_BALANCES_QUERY_KEY });
    },
    onError: () => {
      setError('Unable to create the gift certificate invoice.');
      setMessage(null);
    },
  });

  const redeemMutation = useMutation({
    mutationFn: () => redeemPortalGiftCertificate(redeemCode.trim()),
    onSuccess: (balances) => {
      setRedeemMessage(
        `Gift certificate redeemed. Store credit balance: $${Number(balances.store_credit.balance).toFixed(2)}`,
      );
      setRedeemError(null);
      queryClient.invalidateQueries({ queryKey: STORE_BALANCES_QUERY_KEY });
    },
    onError: () => {
      setRedeemError('Unable to redeem that code. Please verify the characters.');
      setRedeemMessage(null);
    },
  });

  const handlePurchase = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!purchaseAmount || Number(purchaseAmount) <= 0) {
      setError('Enter an amount greater than zero.');
      setMessage(null);
      return;
    }
    purchaseMutation.mutate();
  };

  const handleRedeem = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!redeemCode.trim()) {
      setRedeemError('Enter a gift certificate code.');
      setRedeemMessage(null);
      return;
    }
    redeemMutation.mutate();
  };

  return (
    <div className="grid gap-6 md:grid-cols-2">
      <section className="space-y-4">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Buy a gift certificate</h3>
          <p className="text-sm text-slate-500">Send a digital gift to friends or family. We’ll create an invoice you can pay online.</p>
        </div>
        {message && <p className="rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700">{message}</p>}
        {error && <p className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">{error}</p>}
        <form className="space-y-3" onSubmit={handlePurchase}>
          <label className="flex flex-col text-sm font-medium text-slate-700">
            Amount
            <input
              type="number"
              min={1}
              step="0.01"
              value={purchaseAmount}
              onChange={(event) => setPurchaseAmount(event.target.value)}
              className="mt-1 rounded-lg border border-slate-300 px-3 py-2 focus:border-orange-500 focus:outline-none"
            />
          </label>
          <label className="flex flex-col text-sm font-medium text-slate-700">
            Recipient email <span className="text-xs font-normal text-slate-400">(optional)</span>
            <input
              type="email"
              value={recipientEmail}
              onChange={(event) => setRecipientEmail(event.target.value)}
              className="mt-1 rounded-lg border border-slate-300 px-3 py-2 focus:border-orange-500 focus:outline-none"
              placeholder="friend@example.com"
            />
          </label>
          <button
            type="submit"
            disabled={purchaseMutation.isPending}
            className="w-full rounded-lg bg-orange-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-orange-600 disabled:cursor-not-allowed disabled:bg-orange-300"
          >
            {purchaseMutation.isPending ? 'Creating…' : 'Create invoice'}
          </button>
        </form>
      </section>

      <section className="space-y-4">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Redeem a code</h3>
          <p className="text-sm text-slate-500">Apply an existing gift certificate to your store credit balance.</p>
        </div>
        {redeemMessage && (
          <p className="rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700">{redeemMessage}</p>
        )}
        {redeemError && <p className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">{redeemError}</p>}
        <form className="space-y-3" onSubmit={handleRedeem}>
          <label className="flex flex-col text-sm font-medium text-slate-700">
            Gift certificate code
            <input
              type="text"
              value={redeemCode}
              onChange={(event) => setRedeemCode(event.target.value)}
              className="mt-1 rounded-lg border border-slate-300 px-3 py-2 uppercase focus:border-orange-500 focus:outline-none"
              placeholder="EIPR-XXXX"
            />
          </label>
          <button
            type="submit"
            disabled={redeemMutation.isPending}
            className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {redeemMutation.isPending ? 'Redeeming…' : 'Redeem'}
          </button>
        </form>
      </section>
    </div>
  );
};

export default StoreGiftCerts;
