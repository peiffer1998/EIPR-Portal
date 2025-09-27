import { useMemo, useState } from "react";
import LocationSelect from "../../components/LocationSelect";
import { getDailyAvailability } from "../../lib/capacityFetchers";

export default function ReportsAvailability(){
  const [loc,setLoc]=useState<string>(localStorage.getItem("defaultLocationId")||"");
  const [rtype,setRtype]=useState<"boarding"|"daycare"|"grooming">("boarding");
  const [from,setFrom]=useState<string>(new Date().toISOString().slice(0,10));
  const [to,setTo]=useState<string>(new Date(Date.now()+6*864e5).toISOString().slice(0,10));
  const [rows,setRows]=useState<any[]|null>(null);
  const [busy,setBusy]=useState(false);

  async function run(){
    if(!loc) return;
    setBusy(true);
    try{ const r=await getDailyAvailability(loc, rtype, from, to); setRows(r.days||[]); }
    finally{ setBusy(false); }
  }

  const total = useMemo(()=>{
    const d = rows||[]; return {
      capacity: d.reduce((s:any,x:any)=> s + (x.capacity ?? 0), 0),
      booked:   d.reduce((s:any,x:any)=> s + (x.booked ?? 0), 0),
      available:d.reduce((s:any,x:any)=> s + (x.available ?? 0), 0),
    };
  },[rows]);

  return (
    <div className="grid gap-3">
      <div className="bg-white p-3 rounded-xl shadow grid md:grid-cols-[1fr_1fr_1fr_1fr_auto] gap-2 items-end">
        <div><div className="text-sm text-slate-600">Location</div><LocationSelect value={loc} onChange={(id)=>{ setLoc(id); localStorage.setItem("defaultLocationId",id); }}/></div>
        <div><div className="text-sm text-slate-600">Service</div>
          <select className="border rounded px-3 py-2" value={rtype} onChange={e=>setRtype(e.target.value as any)}>
            <option value="boarding">BOARDING</option><option value="daycare">DAYCARE</option><option value="grooming">GROOMING</option>
          </select>
        </div>
        <div><div className="text-sm text-slate-600">From</div><input type="date" className="border rounded px-3 py-2" value={from} onChange={e=>setFrom(e.target.value)}/></div>
        <div><div className="text-sm text-slate-600">To</div><input type="date" className="border rounded px-3 py-2" value={to} onChange={e=>setTo(e.target.value)}/></div>
        <button className="px-3 py-2 rounded bg-slate-900 text-white" onClick={run} disabled={!loc||busy}>{busy?"Loading…":"Run"}</button>
      </div>

      {rows && <div className="bg-white p-4 rounded-xl shadow">
        <div className="text-sm text-slate-600 mb-2">Totals • Capacity: {total.capacity} • Booked: {total.booked} • Available: {total.available}</div>
        <div className="overflow-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-slate-500"><th className="px-3 py-2">Date</th><th>Capacity</th><th>Booked</th><th>Available</th></tr></thead>
            <tbody>
              {(rows||[]).map((d:any)=>(<tr key={d.date} className="border-t">
                <td className="px-3 py-2">{String(d.date).slice(0,10)}</td>
                <td>{d.capacity ?? "—"}</td>
                <td>{d.booked}</td>
                <td>{d.available ?? "—"}</td>
              </tr>))}
              {rows.length===0 && <tr><td colSpan={4} className="px-3 py-4 text-sm text-slate-500">No data</td></tr>}
            </tbody>
          </table>
        </div>
      </div>}
    </div>
  );
}
