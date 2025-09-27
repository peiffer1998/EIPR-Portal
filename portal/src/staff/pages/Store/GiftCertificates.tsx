import { useEffect, useState } from "react";

import OwnerEntry from "../../components/OwnerEntry";
import LedgerTable from "../../components/LedgerTable";
import SmallForm from "../../components/SmallForm";
import { issueGift, listGifts, redeemGift } from "../../lib/storeFetchers";

export default function GiftCertificates() {
  const [ownerId, setOwnerId] = useState("");
  const [rows, setRows] = useState<any[]>([]);

  const refresh = async () => {
    setRows(await listGifts({ limit: 200 }));
  };

  useEffect(() => {
    void refresh();
  }, []);

  return (
    <div className="grid gap-4">
      <OwnerEntry onOwner={setOwnerId} />

      <SmallForm
        title="Issue gift certificate"
        submitLabel="Issue"
        fields={[
          { name: "amount", label: "Amount", type: "number" },
          { name: "recipient_owner_id", label: "Recipient owner ID (optional)" },
        ]}
        onSubmit={async (values) => {
          const amount = Number(values.amount || 0);
          if (amount <= 0) return;
          const recipient = values.recipient_owner_id?.trim() || undefined;
          await issueGift(amount, recipient);
          await refresh();
        }}
      />

      <SmallForm
        title="Redeem gift certificate"
        submitLabel="Redeem"
        fields={[
          { name: "code", label: "Code" },
          { name: "owner_id", label: "Owner ID (defaults to above)" },
        ]}
        onSubmit={async (values) => {
          const targetOwner = values.owner_id?.trim() || ownerId;
          if (!values.code || !targetOwner) return;
          await redeemGift(values.code.trim(), targetOwner);
          await refresh();
        }}
      />

      <div className="rounded-xl bg-white p-4 shadow">
        <h2 className="mb-3 text-xl font-semibold">Gift certificates</h2>
        <LedgerTable
          columns={[
            { key: "code", label: "Code" },
            { key: "status", label: "Status" },
            { key: "amount", label: "Amount", align: "right" },
            { key: "balance", label: "Balance", align: "right" },
          ]}
          rows={rows.map((gift) => ({
            id: gift.id ?? gift.code,
            code: gift.code,
            status: gift.status ?? "ACTIVE",
            amount: `$${(Number(gift.amount) || 0).toFixed(2)}`,
            balance: `$${(Number(gift.balance) || 0).toFixed(2)}`,
          }))}
        />
      </div>
    </div>
  );
}
