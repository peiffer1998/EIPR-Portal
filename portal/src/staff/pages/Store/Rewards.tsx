import { useEffect, useMemo, useState } from "react";

import OwnerEntry from "../../components/OwnerEntry";
import LedgerTable from "../../components/LedgerTable";
import SmallForm from "../../components/SmallForm";
import { addPoints, getRewards, redeemPoints, rewardValueUSD } from "../../lib/storeFetchers";

export default function StoreRewards() {
  const [ownerId, setOwnerId] = useState("");
  const [rewards, setRewards] = useState<{ points: number; ledger: any[] }>({ points: 0, ledger: [] });

  const refresh = async (id: string) => {
    setRewards(await getRewards(id));
  };

  useEffect(() => {
    if (!ownerId) {
      setRewards({ points: 0, ledger: [] });
      return;
    }
    void refresh(ownerId);
  }, [ownerId]);

  const approxValue = useMemo(() => rewardValueUSD(Number(rewards.points || 0)), [rewards.points]);

  return (
    <div className="grid gap-4">
      <OwnerEntry onOwner={setOwnerId} />

      <div className="rounded-xl bg-white p-4 shadow">
        <h2 className="text-xl font-semibold">Points: {rewards.points ?? 0}</h2>
        <div className="text-sm text-slate-600">Approximate value: ${approxValue.toFixed(2)}</div>
        <LedgerTable
          columns={[
            { key: "ts", label: "Date" },
            { key: "type", label: "Type" },
            { key: "points", label: "Points", align: "right" },
            { key: "note", label: "Note" },
          ]}
          rows={(rewards.ledger ?? []).map((entry) => ({
            id: entry.id ?? entry.ts,
            ts: entry.ts ?? entry.date ?? "",
            type: entry.type ?? "",
            points: entry.points ?? 0,
            note: entry.note ?? "",
          }))}
        />
      </div>

      <SmallForm
        title="Add points"
        submitLabel="Add"
        fields={[
          { name: "points", label: "Points", type: "number" },
          { name: "reason", label: "Reason" },
        ]}
        onSubmit={async (values) => {
          if (!ownerId) return;
          const points = Number(values.points || 0);
          if (points <= 0) return;
          await addPoints(ownerId, points, values.reason?.trim() || undefined);
          await refresh(ownerId);
        }}
      />

      <SmallForm
        title="Redeem points"
        submitLabel="Redeem"
        fields={[
          { name: "points", label: "Points", type: "number" },
          { name: "reason", label: "Reason" },
        ]}
        onSubmit={async (values) => {
          if (!ownerId) return;
          const points = Number(values.points || 0);
          if (points <= 0) return;
          await redeemPoints(ownerId, points, values.reason?.trim() || undefined);
          await refresh(ownerId);
        }}
      />
    </div>
  );
}
