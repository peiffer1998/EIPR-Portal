import { useEffect, useMemo, useReducer, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import Button from "../../../ui/Button";
import { Card } from "../../../ui/Card";
import Page from "../../../ui/Page";
import Table from "../../../ui/Table";
import BoardFilters from "../../components/BoardFilters";
import ProgramSelect from "../../components/ProgramSelect";
import GroupChip from "../../components/GroupChip";
import IncidentDialog from "../../components/IncidentDialog";
import {
  assignGroup,
  checkIn,
  checkOut,
  getDaycareRoster,
  logIncident,
} from "../../lib/daycareFetchers";
import {
  getSelectedIds,
  initialSelection,
  selectionReducer,
} from "./rosterState";

const standingLabel = "Standing reservation";

type FilterState = {
  date: string;
  location_id: string;
  area?: string;
  q?: string;
};

type GroupFilter = string | null | "__all";

function formatOwner(owner: { first_name?: string; last_name?: string } | null) {
  if (!owner) return "";
  const name = `${owner.first_name || ""} ${owner.last_name || ""}`.trim();
  return name || "";
}

export default function DaycareRoster() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<FilterState>({
    date: new Date().toISOString().slice(0, 10),
    location_id: localStorage.getItem("defaultLocationId") || "",
  });
  const [program, setProgram] = useState<string>("");
  const [groupFilter, setGroupFilter] = useState<GroupFilter>("__all");
  const [selection, dispatchSelection] = useReducer(selectionReducer, initialSelection);
  const [incidentTarget, setIncidentTarget] = useState<string | null>(null);
  const [assigning, setAssigning] = useState<string | null>(null);
  const [assignDraft, setAssignDraft] = useState<string>("");

  const rosterQuery = useQuery({
    queryKey: ["daycare", filters.date, filters.location_id, program],
    queryFn: () => getDaycareRoster(filters.date, filters.location_id, program || undefined),
    enabled: Boolean(filters.date && filters.location_id),
  });

  useEffect(() => {
    dispatchSelection({ type: "clear" });
  }, [filters.date, filters.location_id, program]);

  const availableGroups = useMemo(() => {
    const raw = Array.isArray(rosterQuery.data) ? rosterQuery.data : [];
    const groups = new Set<string>();
    raw.forEach((row) => {
      if (row.group) groups.add(row.group);
    });
    return Array.from(groups).sort((a, b) => a.localeCompare(b));
  }, [rosterQuery.data]);

  const visibleRows = useMemo(() => {
    let rows = Array.isArray(rosterQuery.data) ? rosterQuery.data : [];
    if (filters.q) {
      const needle = filters.q.toLowerCase();
      rows = rows.filter((row) => {
        const pet = row.pet?.name?.toLowerCase() ?? "";
        const owner = formatOwner(row.owner).toLowerCase();
        return pet.includes(needle) || owner.includes(needle);
      });
    }
    if (groupFilter && groupFilter !== "__all") {
      rows = rows.filter((row) => (groupFilter === null ? !row.group : row.group === groupFilter));
    }
    return rows.sort((a, b) => (a.pet?.name || "").localeCompare(b.pet?.name || ""));
  }, [rosterQuery.data, filters.q, groupFilter]);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["daycare"] });

  const checkInMutation = useMutation({
    mutationFn: (id: string) => checkIn(id),
    onSuccess: invalidate,
  });

  const checkOutMutation = useMutation({
    mutationFn: (payload: { id: string; late: boolean }) => checkOut(payload.id, payload.late),
    onSuccess: invalidate,
  });

  const assignGroupMutation = useMutation({
    mutationFn: (payload: { id: string; group: string }) => assignGroup(payload.id, payload.group),
    onSuccess: invalidate,
  });

  const incidentMutation = useMutation({
    mutationFn: (payload: { id: string; type: string; note: string }) =>
      logIncident({ reservation_id: payload.id, type: payload.type, note: payload.note }),
  });

  const setAllSelected = (checked: boolean) => {
    if (!checked) {
      dispatchSelection({ type: "clear" });
      return;
    }
    const next: Record<string, boolean> = {};
    visibleRows.forEach((row) => {
      next[row.id] = true;
    });
    dispatchSelection({ type: "replace", next });
  };

  const bulkCheckOut = async (late: boolean) => {
    const ids = getSelectedIds(selection);
    if (ids.length === 0) return;
    await Promise.all(ids.map((id) => checkOut(id, late).catch(() => undefined)));
    dispatchSelection({ type: "clear" });
    invalidate();
  };

  const startAssigning = (rowId: string, currentGroup: string | null) => {
    setAssigning(rowId);
    setAssignDraft(currentGroup ?? "");
  };

  const commitAssign = async () => {
    if (!assigning) return;
    const value = assignDraft.trim();
    if (!value) {
      setAssigning(null);
      return;
    }
    await assignGroupMutation.mutateAsync({ id: assigning, group: value });
    setAssigning(null);
  };

  const standingCount = visibleRows.filter((row) => row.standing).length;

  return (
    <Page>
      <Page.Header
        title="Daycare Roster"
        sub="Manage groups, incidents, and check-outs"
      />

      <Card>
        <BoardFilters onChange={setFilters} />
      </Card>

      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-600">Program</span>
              <ProgramSelect locationId={filters.location_id} value={program} onChange={setProgram} />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-600">Groups</span>
              <button
                type="button"
                className={`rounded-full px-2 py-1 text-[11px] ${groupFilter === "__all" ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-700"}`}
                onClick={() => setGroupFilter("__all")}
              >
                All
              </button>
              <GroupChip value={null} onClick={() => setGroupFilter(null)} active={groupFilter === null} />
              {availableGroups.map((group) => (
                <GroupChip
                  key={group}
                  value={group}
                  onClick={() => setGroupFilter(group)}
                  active={groupFilter === group}
                />
              ))}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button type="button" className="text-sm" onClick={() => bulkCheckOut(false)}>
              Bulk Check-Out
            </Button>
            <Button
              type="button"
              variant="secondary"
              className="text-sm"
              onClick={() => bulkCheckOut(true)}
            >
              Bulk Late Check-Out
            </Button>
          </div>
        </div>
      </Card>

      {standingCount > 0 ? (
        <Card className="border border-amber-200 bg-amber-50 text-sm text-amber-700">
          {standingCount} attendee{standingCount === 1 ? "" : "s"} have a {standingLabel} today.
        </Card>
      ) : null}

      <Card className="overflow-auto">
        <Table>
          <thead className="text-left text-slate-500">
            <tr>
              <th className="px-3 py-2">
                <input
                  type="checkbox"
                  checked={
                    visibleRows.length > 0 &&
                    visibleRows.every((row) => selection[row.id])
                  }
                  onChange={(event) => setAllSelected(event.target.checked)}
                />
              </th>
              <th className="px-3 py-2">Pet</th>
              <th className="px-3 py-2">Owner</th>
              <th className="px-3 py-2">Program</th>
              <th className="px-3 py-2">Group</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row) => {
              const isCheckedIn = row.status === "CHECKED_IN";
              const rowHighlight = row.late_pickup ? "bg-rose-50" : "";
              return (
                <tr key={row.id} className={`border-t ${rowHighlight}`}>
                  <td className="px-3 py-2">
                    <input
                      type="checkbox"
                      checked={Boolean(selection[row.id])}
                      onChange={() => dispatchSelection({ type: "toggle", id: row.id })}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <div className="font-medium">{row.pet?.name || row.id}</div>
                    {row.standing ? (
                      <div className="text-xs text-amber-600">{standingLabel}</div>
                    ) : null}
                  </td>
                  <td>
                    <div>{formatOwner(row.owner)}</div>
                    {row.check_in_at ? (
                      <div className="text-[11px] text-slate-500">In: {row.check_in_at}</div>
                    ) : null}
                    {row.check_out_at ? (
                      <div className="text-[11px] text-slate-500">Out: {row.check_out_at}</div>
                    ) : null}
                  </td>
                  <td>{row.program}</td>
                  <td>
                    <GroupChip value={row.group} />
                    {assigning === row.id ? (
                      <div className="mt-2 flex items-center gap-2">
                        <select
                          className="rounded border px-2 py-1 text-xs"
                          value={assignDraft}
                          onChange={(event) => setAssignDraft(event.target.value)}
                        >
                          <option value="">Select or type…</option>
                          {availableGroups.map((group) => (
                            <option key={group} value={group}>
                              {group}
                            </option>
                          ))}
                        </select>
                        <input
                          className="rounded border px-2 py-1 text-xs"
                          placeholder="Custom"
                          value={assignDraft}
                          onChange={(event) => setAssignDraft(event.target.value)}
                        />
                        <button
                          type="button"
                          className="rounded bg-slate-900 px-2 py-1 text-xs text-white"
                          onClick={commitAssign}
                        >
                          Save
                        </button>
                        <button
                          type="button"
                          className="rounded px-2 py-1 text-xs"
                          onClick={() => setAssigning(null)}
                        >
                          Cancel
                        </button>
                      </div>
                    ) : null}
                  </td>
                  <td>
                    <div className="font-medium">{row.status}</div>
                    {row.late_pickup ? (
                      <div className="text-xs text-rose-600">Late pickup flagged</div>
                    ) : null}
                  </td>
                  <td className="py-2">
                    <div className="flex flex-wrap gap-2">
                      {!isCheckedIn ? (
                        <button
                          type="button"
                          className="rounded bg-green-600 px-2 py-1 text-xs text-white"
                          onClick={() => checkInMutation.mutate(row.id)}
                        >
                          Check-In
                        </button>
                      ) : null}
                      {isCheckedIn ? (
                        <>
                          <button
                            type="button"
                            className="rounded bg-slate-700 px-2 py-1 text-xs text-white"
                            onClick={() => checkOutMutation.mutate({ id: row.id, late: false })}
                          >
                            Check-Out
                          </button>
                          <button
                            type="button"
                            className="rounded bg-amber-600 px-2 py-1 text-xs text-white"
                            onClick={() => checkOutMutation.mutate({ id: row.id, late: true })}
                          >
                            Late Out
                          </button>
                        </>
                      ) : null}
                      <button
                        type="button"
                        className="rounded border px-2 py-1 text-xs"
                        onClick={() => startAssigning(row.id, row.group)}
                      >
                        Assign Group
                      </button>
                      <button
                        type="button"
                        className="rounded border px-2 py-1 text-xs"
                        onClick={() => setIncidentTarget(row.id)}
                      >
                        Log Incident
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
            {visibleRows.length === 0 && !rosterQuery.isFetching ? (
              <tr>
                <td colSpan={7} className="px-3 py-5 text-center text-sm text-slate-500">
                  No daycare reservations for this selection.
                </td>
              </tr>
            ) : null}
          </tbody>
        </Table>
      </Card>

      <IncidentDialog
        open={incidentTarget !== null}
        onClose={() => setIncidentTarget(null)}
        onSubmit={async ({ type, note }) => {
          if (!incidentTarget) return;
          await incidentMutation.mutateAsync({ id: incidentTarget, type, note });
        }}
      />
    </Page>
  );
}
