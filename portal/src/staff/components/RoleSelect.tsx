import { useEffect, useState } from "react";

import { listRoles } from "../lib/invitationsFetchers";

interface Props {
  value?: string;
  onChange: (role: string) => void;
}

export default function RoleSelect({ value, onChange }: Props) {
  const [roles, setRoles] = useState<string[]>(["SUPERADMIN", "ADMIN", "MANAGER", "STAFF"]);

  useEffect(() => {
    void listRoles().then(setRoles).catch(() => {});
  }, []);

  return (
    <select className="border rounded px-3 py-2" value={value ?? ""} onChange={(event) => onChange(event.target.value)}>
      <option value="">Pick a role</option>
      {roles.map((role) => (
        <option key={role} value={role}>
          {role}
        </option>
      ))}
    </select>
  );
}
