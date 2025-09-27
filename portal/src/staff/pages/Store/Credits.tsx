import { useEffect, useState } from "react";

import OwnerEntry from "../../components/OwnerEntry";
import LedgerTable from "../../components/LedgerTable";
import Money from "../../components/Money";
import SmallForm from "../../components/SmallForm";
import {
  addStoreCredit,
  applyCreditToInvoice,
  getStoreCredit,
} from "../../lib/storeFetchers";

export default function StoreCredits() {
  const [ownerId, setOwnerId] = useState("");
  const [credit, setCredit] = useState<{ balance: number; ledger: any[] }>({ balance: 0, ledger: [] });

  const refresh = async (id: string) => {
    setCredit(await getStoreCredit(id));
  };

  useEffect(() => {
    if (!ownerId) {
      setCredit({ balance: 0, ledger: [] });
      return;
    }
    void refresh(ownerId);
  }, [ownerId]);

  return (
    <div className="grid gap-4">
      <OwnerEntry onOwner={setOwnerId} />

      <div className="rounded-xl bg-white p-4 shadow">
        <h2 className="text-xl font-semibold">
          Balance: <Money value={credit.balance ?? 0} />
        </h2>
        <LedgerTable
          columns={[
            { key: "ts", label: "Date" },
            { key: "type", label: "Type" },
            { key: "amount", label: "Amount", align: "right" },
            { key: "note", label: "Note" },
          ]}
          rows={(credit.ledger ?? []).map((entry) => ({
            id: entry.id ?? entry.ts,
            ts: entry.ts ?? entry.date ?? "",
            type: entry.type ?? "",
            amount: `$${(Number(entry.amount) || 0).toFixed(2)}`,
            note: entry.note ?? "",
          }))}
        />
      </div>

      <SmallForm
        title="Add store credit"
        submitLabel="Add"
        fields={[
          { name: "amount", label: "Amount", type: "number" },
          { name: "note", label: "Note" },
        ]}
        onSubmit={async (values) => {
          if (!ownerId) return;
          const amount = Number(values.amount || 0);
          if (amount <= 0) return;
          await addStoreCredit(ownerId, amount, values.note?.trim() || undefined);
          await refresh(ownerId);
        }}
      />

      <SmallForm
        title="Apply to invoice"
        submitLabel="Apply"
        fields={[
          { name: "invoice_id", label: "Invoice ID" },
          { name: "amount", label: "Amount", type: "number" },
        ]}
        onSubmit={async (values) => {
          if (!ownerId) return;
          const amount = Number(values.amount || 0);
          const invoiceId = values.invoice_id?.trim();
          if (amount <= 0 || !invoiceId) return;
          await applyCreditToInvoice(ownerId, invoiceId, amount);
          await refresh(ownerId);
        }}
      />
    </div>
  );
}
