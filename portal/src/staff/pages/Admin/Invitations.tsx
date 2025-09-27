import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import CopyButton from "../../components/CopyButton";
import InvitationDrawer from "../../components/InvitationDrawer";
import SearchBox from "../../components/SearchBox";
import {
  createInvitation,
  listInvitations,
  resendInvitation,
  revokeInvitation,
} from "../../lib/invitationsFetchers";

const formatLink = (token?: string) => {
  if (!token) return "";
  try {
    return `${window.location.origin}/invite/accept?token=${encodeURIComponent(token)}`;
  } catch {
    return `/invite/accept?token=${encodeURIComponent(token)}`;
  }
};

type Row = {
  id: string;
  email: string;
  name: string;
  role: string;
  status: string;
  expires_at?: string;
  token?: string;
};

export default function AdminInvitations() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);

  const listQuery = useQuery({
    queryKey: ["invitations"],
    queryFn: () => listInvitations({ limit: 200 }),
  });

  const rows = useMemo<Row[]>(() => {
    const mapped = (listQuery.data || []).map((invite: any) => ({
      id: String(invite.id),
      email: invite.email,
      name: `${invite.first_name ?? ""} ${invite.last_name ?? ""}`.trim(),
      role: invite.role,
      status: invite.status ?? "pending",
      expires_at: invite.expires_at,
      token: invite.token,
    }));

    if (!search) return mapped;
    const needle = search.toLowerCase();
    return mapped.filter(
      (row) => row.email.toLowerCase().includes(needle) || row.name.toLowerCase().includes(needle),
    );
  }, [listQuery.data, search]);

  const createMutation = useMutation({
    mutationFn: createInvitation,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["invitations"] }),
  });

  const resendMutation = useMutation({
    mutationFn: resendInvitation,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["invitations"] }),
  });

  const revokeMutation = useMutation({
    mutationFn: revokeInvitation,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["invitations"] }),
  });

  return (
    <div className="grid gap-3">
      <div className="bg-white p-3 rounded-xl shadow flex items-center justify-between">
        <SearchBox onChange={setSearch} placeholder="Search invites" />
        <button
          className="px-3 py-2 rounded bg-slate-900 text-white"
          type="button"
          onClick={() => setDrawerOpen(true)}
        >
          Invite Staff
        </button>
      </div>

      <div className="bg-white rounded-xl shadow overflow-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-white border-b">
            <tr className="text-left text-slate-500">
              <th className="px-3 py-2">Email</th>
              <th>Name</th>
              <th>Role</th>
              <th>Status</th>
              <th>Expires</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-t">
                <td className="px-3 py-2">{row.email}</td>
                <td>{row.name || "—"}</td>
                <td>{row.role}</td>
                <td>{row.status}</td>
                <td>{row.expires_at ? row.expires_at.slice(0, 16).replace("T", " ") : "—"}</td>
                <td className="py-2">
                  <div className="flex gap-2">
                    {row.token ? <CopyButton text={formatLink(row.token)} /> : null}
                    <button
                      className="px-2 py-1 rounded border text-xs"
                      type="button"
                      onClick={() => resendMutation.mutate(row.id)}
                    >
                      Resend
                    </button>
                    <button
                      className="px-2 py-1 rounded border text-xs text-red-600"
                      type="button"
                      onClick={() => revokeMutation.mutate(row.id)}
                    >
                      Revoke
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {rows.length === 0 && !listQuery.isFetching && (
              <tr>
                <td colSpan={6} className="px-3 py-4 text-sm text-slate-500">
                  No invitations
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <InvitationDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onCreate={async (payload) => {
          await createMutation.mutateAsync(payload);
          setDrawerOpen(false);
        }}
      />
    </div>
  );
}
