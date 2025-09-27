import { useEffect, useState } from "react";

import RoleSelect from "./RoleSelect";

interface Props {
  open: boolean;
  onClose: () => void;
  onCreate: (payload: {
    email: string;
    first_name?: string;
    last_name?: string;
    role: string;
    location_ids?: string[];
    expires_days?: number;
  }) => Promise<void>;
}

export default function InvitationDrawer({ open, onClose, onCreate }: Props) {
  const [values, setValues] = useState({
    email: "",
    first_name: "",
    last_name: "",
    role: "STAFF",
    location_ids: "",
    expires_days: 14,
  });

  useEffect(() => {
    if (open) {
      setValues({ email: "", first_name: "", last_name: "", role: "STAFF", location_ids: "", expires_days: 14 });
    }
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/30 z-50">
      <div className="absolute right-0 top-0 h-full w-[440px] bg-white shadow-xl p-4 grid gap-2">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Invite Staff</h3>
          <button className="text-sm" type="button" onClick={onClose}>
            Close
          </button>
        </div>

        <label className="text-sm grid">
          <span>Email</span>
          <input
            className="border rounded px-3 py-2"
            value={values.email}
            onChange={(event) => setValues((prev) => ({ ...prev, email: event.target.value }))}
          />
        </label>

        <label className="text-sm grid">
          <span>First name</span>
          <input
            className="border rounded px-3 py-2"
            value={values.first_name}
            onChange={(event) => setValues((prev) => ({ ...prev, first_name: event.target.value }))}
          />
        </label>

        <label className="text-sm grid">
          <span>Last name</span>
          <input
            className="border rounded px-3 py-2"
            value={values.last_name}
            onChange={(event) => setValues((prev) => ({ ...prev, last_name: event.target.value }))}
          />
        </label>

        <label className="text-sm grid">
          <span>Role</span>
          <RoleSelect value={values.role} onChange={(role) => setValues((prev) => ({ ...prev, role }))} />
        </label>

        <label className="text-sm grid">
          <span>Location IDs (comma separated, optional)</span>
          <input
            className="border rounded px-3 py-2"
            value={values.location_ids}
            onChange={(event) => setValues((prev) => ({ ...prev, location_ids: event.target.value }))}
          />
        </label>

        <label className="text-sm grid">
          <span>Expires in days</span>
          <input
            className="border rounded px-3 py-2"
            type="number"
            value={values.expires_days}
            onChange={(event) =>
              setValues((prev) => ({ ...prev, expires_days: Number(event.target.value || 14) }))
            }
          />
        </label>

        <div className="mt-2 flex justify-end">
          <button
            className="px-3 py-2 rounded bg-slate-900 text-white"
            type="button"
            onClick={() =>
              onCreate({
                email: values.email,
                first_name: values.first_name || undefined,
                last_name: values.last_name || undefined,
                role: values.role,
                location_ids: values.location_ids
                  ? values.location_ids.split(",").map((id) => id.trim()).filter(Boolean)
                  : undefined,
                expires_days: values.expires_days || 14,
              })
            }
          >
            Send Invite
          </button>
        </div>
      </div>
    </div>
  );
}
