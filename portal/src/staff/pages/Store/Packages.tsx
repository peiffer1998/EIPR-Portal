import { useEffect, useState } from "react";

import OwnerEntry from "../../components/OwnerEntry";
import LedgerTable from "../../components/LedgerTable";
import Money from "../../components/Money";
import {
  consumeOwnerPackage,
  listOwnerPackages,
  listPackages,
  sellPackage,
} from "../../lib/storeFetchers";

export default function StorePackages() {
  const [ownerId, setOwnerId] = useState("");
  const [available, setAvailable] = useState<any[]>([]);
  const [ownerPackages, setOwnerPackages] = useState<any[]>([]);

  useEffect(() => {
    void listPackages()
      .then(setAvailable)
      .catch(() => setAvailable([]));
  }, []);

  useEffect(() => {
    if (!ownerId) {
      setOwnerPackages([]);
      return;
    }
    void listOwnerPackages(ownerId)
      .then(setOwnerPackages)
      .catch(() => setOwnerPackages([]));
  }, [ownerId]);

  const refreshOwnerPackages = async () => {
    if (!ownerId) return;
    setOwnerPackages(await listOwnerPackages(ownerId));
  };

  const handleSell = async (packageId: string) => {
    if (!ownerId) return;
    await sellPackage(ownerId, packageId, 1);
    await refreshOwnerPackages();
  };

  const handleConsume = async (ownerPackageId: string, amount: number) => {
    if (!ownerPackageId || amount <= 0) return;
    await consumeOwnerPackage(ownerPackageId, amount);
    await refreshOwnerPackages();
  };

  return (
    <div className="grid gap-4">
      <OwnerEntry onOwner={setOwnerId} />

      <div className="rounded-xl bg-white p-4 shadow">
        <h2 className="mb-3 text-xl font-semibold">Available Packages</h2>
        <div className="grid gap-3 md:grid-cols-3">
          {available.map((pkg) => (
            <div key={pkg.id} className="rounded-lg border p-3">
              <div className="font-semibold">{pkg.name ?? pkg.id}</div>
              <div className="text-sm text-slate-600">
                Credits: {pkg.qty ?? pkg.quantity ?? 1} • <Money value={pkg.price ?? 0} />
              </div>
              <button
                type="button"
                className="mt-3 rounded bg-slate-900 px-3 py-2 text-white"
                disabled={!ownerId}
                onClick={() => handleSell(pkg.id)}
              >
                Sell to owner
              </button>
            </div>
          ))}
          {available.length === 0 && <div className="text-sm text-slate-500">No packages configured.</div>}
        </div>
      </div>

      <div className="rounded-xl bg-white p-4 shadow">
        <h2 className="mb-3 text-xl font-semibold">Owner Packages</h2>
        <LedgerTable
          columns={[
            { key: "package", label: "Package" },
            { key: "remaining", label: "Remaining", align: "right" },
            { key: "status", label: "Status" },
          ]}
          rows={ownerPackages.map((entry) => ({
            id: entry.id,
            package: entry.package?.name ?? entry.package_name ?? entry.package_id,
            remaining: entry.remaining ?? entry.balance ?? 0,
            status: entry.status ?? "ACTIVE",
          }))}
        />
        <form
          className="mt-4 flex flex-wrap items-end gap-3"
          onSubmit={async (event) => {
            event.preventDefault();
            const formData = new FormData(event.currentTarget);
            const id = String(formData.get("owner_package_id") || "").trim();
            const amount = Number(formData.get("amount") || 0);
            await handleConsume(id, amount);
            event.currentTarget.reset();
          }}
        >
          <label className="grid text-sm">
            <span className="text-slate-600">Owner Package ID</span>
            <input className="border rounded px-3 py-2" name="owner_package_id" />
          </label>
          <label className="grid text-sm">
            <span className="text-slate-600">Amount</span>
            <input className="border rounded px-3 py-2" name="amount" type="number" step="1" />
          </label>
          <button type="submit" className="h-10 rounded bg-slate-900 px-3 py-2 text-white">
            Consume credits
          </button>
        </form>
      </div>
    </div>
  );
}
