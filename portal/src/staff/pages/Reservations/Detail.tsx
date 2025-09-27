import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getReservation, cancelReservation, noShowReservation, checkIn, checkOut, moveRun, listRuns, capacityWindow } from "../../lib/reservationOps";

function Section({title, children}:{title:string; children:React.ReactNode}){ return <div className="bg-white p-6 rounded-xl shadow"><h3 className="text-xl font-semibold mb-2">{title}</h3>{children}</div>; }

export default function ReservationDetail(){
  const { id="" } = useParams(); const nav = useNavigate(); const qc = useQueryClient();
  const { data } = useQuery({ queryKey:["resv", id], queryFn:()=>getReservation(id), enabled:Boolean(id) });
  const r:any = data || {};
  const runs = useQuery({ queryKey:["runs", r.location_id], queryFn:()=>listRuns(r.location_id), enabled:Boolean(r.location_id) });
  const cap  = useQuery({ queryKey:["cap", r.location_id, r.start_at, r.end_at], queryFn:()=>capacityWindow(r.location_id, r.start_at?.slice?.(0,10), r.end_at?.slice?.(0,10), r.reservation_type), enabled:Boolean(r.location_id && r.start_at && r.end_at) });

  const doCheckIn  = useMutation({ mutationFn:(run_id?:string)=>checkIn(id, run_id),  onSuccess:()=>qc.invalidateQueries({queryKey:["resv",id]}) });
  const doCheckOut = useMutation({ mutationFn:()=>checkOut(id),        onSuccess:()=>qc.invalidateQueries({queryKey:["resv",id]}) });
  const doMove     = useMutation({ mutationFn:(run_id:string)=>moveRun(id, run_id), onSuccess:()=>qc.invalidateQueries({queryKey:["resv",id]}) });
  const doCancel   = useMutation({ mutationFn:()=>cancelReservation(id), onSuccess:()=>nav("/staff/reservations") });
  const doNoShow   = useMutation({ mutationFn:()=>noShowReservation(id), onSuccess:()=>nav("/staff/reservations") });

  return (
    <div className="grid gap-4">
      <Section title="Overview">
        <div className="grid md:grid-cols-2 gap-3 text-sm">
          <div><div className="text-slate-500">Pet</div><div className="font-medium">{r.pet?.name || r.pet_id}</div></div>
          <div><div className="text-slate-500">Owner</div><div className="font-medium">{r.owner?.first_name} {r.owner?.last_name}</div></div>
          <div><div className="text-slate-500">Dates</div><div className="font-medium">{r.start_at} → {r.end_at}</div></div>
          <div><div className="text-slate-500">Status</div><div className="font-medium">{r.status}</div></div>
        </div>
        <div className="mt-3 flex gap-2">
          <button className="bg-slate-900 text-white px-3 py-2 rounded" onClick={()=>window.open(`/staff/print/run-card/${id}`,"_blank")}>Print Run Card</button>
          <button className="px-3 py-2 rounded border" onClick={()=>doCancel.mutate()}>Cancel</button>
          <button className="px-3 py-2 rounded border" onClick={()=>doNoShow.mutate()}>No-show</button>
        </div>
      </Section>

      <Section title="Lodging">
        <div className="text-sm mb-2">Current run: <span className="font-medium">{r.run?.name || r.run_id || "Unassigned"}</span></div>
        <div className="flex gap-2 items-end">
          <label className="text-sm grid"><span>Assign/move to run</span>
            <select className="border rounded px-3 py-2" onChange={e=>doMove.mutate(e.target.value)} defaultValue="">
              <option value="" disabled>Choose run</option>
              {(runs.data||[]).map((run:any)=><option key={run.id} value={run.id}>{run.name || run.id}</option>)}
            </select>
          </label>
          <button className="px-3 py-2 rounded border" onClick={()=>doMove.mutate("UNASSIGN")}>Unassign</button>
        </div>
        <div className="mt-3">
          <div className="text-sm text-slate-500">Capacity window</div>
          <pre className="text-xs bg-slate-50 p-2 rounded overflow-auto">{JSON.stringify(cap.data||[], null, 2)}</pre>
        </div>
      </Section>

      <Section title="Actions">
        <div className="flex gap-2">
          <button className="bg-orange-500 text-white px-4 py-2 rounded" onClick={()=>doCheckIn.mutate(r.run_id)}>Check-in</button>
          <button className="bg-slate-900 text-white px-4 py-2 rounded" onClick={()=>doCheckOut.mutate()}>Check-out</button>
        </div>
      </Section>

      <Section title="Charges (coming soon)">
        <div className="text-sm text-slate-600">Line items, discounts, taxes, deposits will show here.</div>
      </Section>

      <Section title="Notes (coming soon)">
        <div className="text-sm text-slate-600">Reservation-level notes editor.</div>
      </Section>
    </div>
  );
}
