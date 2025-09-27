import { useEffect, useState } from "react";

import OwnerEntry from "../../components/OwnerEntry";
import LedgerTable from "../../components/LedgerTable";
import {
  cancelOwnerMembership,
  enrollMembership,
  listMemberships,
  listOwnerMemberships,
} from "../../lib/storeFetchers";

export default function StoreMemberships() {
  const [ownerId, setOwnerId] = useState("");
  const [memberships, setMemberships] = useState<any[]>([]);
  const [ownerMemberships, setOwnerMemberships] = useState<any[]>([]);

  useEffect(() => {
    void listMemberships()
      .then(setMemberships)
      .catch(() => setMemberships([]));
  }, []);

  useEffect(() => {
    if (!ownerId) {
      setOwnerMemberships([]);
      return;
    }
    void listOwnerMemberships(ownerId)
      .then(setOwnerMemberships)
      .catch(() => setOwnerMemberships([]));
  }, [ownerId]);

  const refreshOwnerMemberships = async () => {
    if (!ownerId) return;
    setOwnerMemberships(await listOwnerMemberships(ownerId));
  };

  const handleEnroll = async (membershipId: string) => {
    if (!ownerId) return;
    const today = new Date().toISOString().slice(0, 10);
    await enrollMembership(ownerId, membershipId, today);
    await refreshOwnerMemberships();
  };

  const handleCancel = async (ownerMembershipId: string) => {
    if (!ownerMembershipId) return;
    await cancelOwnerMembership(ownerMembershipId);
    await refreshOwnerMemberships();
  };

  return (
    <div className="grid gap-4">
      <OwnerEntry onOwner={setOwnerId} />

      <div className="rounded-xl bg-white p-4 shadow">
        <h2 className="mb-3 text-xl font-semibold">Memberships</h2>
        <div className="grid gap-3 md:grid-cols-3">
          {memberships.map((membership) => (
            <div key={membership.id} className="rounded-lg border p-3">
              <div className="font-semibold">{membership.name ?? membership.id}</div>
              <div className="text-sm text-slate-600">Billing: {membership.billing_period ?? "Monthly"}</div>
              <button
                type="button"
                className="mt-3 rounded bg-slate-900 px-3 py-2 text-white"
                disabled={!ownerId}
                onClick={() => handleEnroll(membership.id)}
              >
                Enroll owner
              </button>
            </div>
          ))}
          {memberships.length === 0 && <div className="text-sm text-slate-500">No memberships configured.</div>}
        </div>
      </div>

      <div className="rounded-xl bg-white p-4 shadow">
        <h2 className="mb-3 text-xl font-semibold">Owner Memberships</h2>
        <LedgerTable
          columns={[
            { key: "name", label: "Membership" },
            { key: "status", label: "Status" },
            { key: "renews", label: "Renews on" },
          ]}
          rows={ownerMemberships.map((entry) => ({
            id: entry.id,
            name: entry.membership?.name ?? entry.membership_name ?? entry.membership_id,
            status: entry.status ?? "ACTIVE",
            renews: entry.renews_on ?? entry.next_bill_date ?? "",
          }))}
        />
        <form
          className="mt-4 flex flex-wrap items-end gap-3"
          onSubmit={async (event) => {
            event.preventDefault();
            const formData = new FormData(event.currentTarget);
            const id = String(formData.get("owner_membership_id") || "").trim();
            await handleCancel(id);
            event.currentTarget.reset();
          }}
        >
          <label className="grid text-sm">
            <span className="text-slate-600">Owner Membership ID</span>
            <input className="border rounded px-3 py-2" name="owner_membership_id" />
          </label>
          <button type="submit" className="h-10 rounded bg-slate-900 px-3 py-2 text-white">
            Cancel membership
          </button>
        </form>
      </div>
    </div>
  );
}
